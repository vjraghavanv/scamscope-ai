# Deployment (Phase 2) — GATED

> ⚠️ **Do not run these steps until deployment is explicitly approved.** They create
> AWS resources (a secret, an IAM role, and a Lambda function) and may incur cost.
> Phase 1 (the baseline agent) needs none of this.

Set your variables:

```bash
export AWS_REGION=us-east-1
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export FN=check_url_reputation
```

## 1. Store the URLhaus Auth-Key in Secrets Manager

Get an Auth-Key from your abuse.ch account (https://auth.abuse.ch/). Then:

```bash
aws secretsmanager create-secret \
  --name scamscope/urlhaus-auth-key \
  --secret-string '{"auth_key":"YOUR_URLHAUS_AUTH_KEY"}' \
  --region "$AWS_REGION"
```

The value lives only in Secrets Manager — never in code, env files, or the repo.

## 2. Create the least-privilege execution role

`infra/iam_policy.json` grants exactly two things: read the one secret, write this
function's own logs. Substitute the placeholders first:

```bash
sed -e "s/REGION/$AWS_REGION/g" -e "s/ACCOUNT_ID/$ACCOUNT_ID/g" \
  infra/iam_policy.json > /tmp/scamscope-policy.json

cat > /tmp/trust.json <<'JSON'
{ "Version":"2012-10-17","Statement":[{"Effect":"Allow",
  "Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}
JSON

aws iam create-role --role-name scamscope-lambda-role \
  --assume-role-policy-document file:///tmp/trust.json
aws iam put-role-policy --role-name scamscope-lambda-role \
  --policy-name scamscope-least-privilege \
  --policy-document file:///tmp/scamscope-policy.json
```

## 3. Package and create the Lambda

```bash
cd lambda/check_url_reputation
pip install -r requirements.txt -t build
cp handler.py build/
( cd build && zip -r ../function.zip . )

aws lambda create-function \
  --function-name "$FN" \
  --runtime python3.12 \
  --handler handler.handler \
  --timeout 15 \
  --memory-size 256 \
  --role "arn:aws:iam::$ACCOUNT_ID:role/scamscope-lambda-role" \
  --environment "Variables={SCAMSCOPE_URLHAUS_SECRET_NAME=scamscope/urlhaus-auth-key}" \
  --zip-file fileb://function.zip \
  --region "$AWS_REGION"
```

The 15 s function timeout plus the handler's 3 s/8 s connect/read timeouts bound the
blast radius of a slow URLhaus response.

## 4. Allow the agent's caller to invoke it

The principal running the agent needs only:

```json
{ "Effect":"Allow","Action":"lambda:InvokeFunction",
  "Resource":"arn:aws:lambda:REGION:ACCOUNT_ID:function:check_url_reputation" }
```

## 5. Smoke test the deployed function (safe sample)

```bash
aws lambda invoke --function-name "$FN" \
  --payload '{"url":"http://not-a-real-host.invalid/test"}' \
  --cli-binary-format raw-in-base64-out /tmp/out.json --region "$AWS_REGION"
cat /tmp/out.json
```

## Teardown

```bash
aws lambda delete-function --function-name "$FN" --region "$AWS_REGION"
aws iam delete-role-policy --role-name scamscope-lambda-role --policy-name scamscope-least-privilege
aws iam delete-role --role-name scamscope-lambda-role
aws secretsmanager delete-secret --secret-id scamscope/urlhaus-auth-key \
  --force-delete-without-recovery --region "$AWS_REGION"
```
