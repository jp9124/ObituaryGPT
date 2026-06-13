Put your Terraform configuration in the [`main.tf`](main.tf) file.

Before running `terraform apply`, create these SecureString parameters in AWS
Systems Manager Parameter Store under `/last-show/<your-ucid>/`:

- `openai_api_key`
- `cloudinary_cloud_name`
- `cloudinary_api_key`
- `cloudinary_api_secret`

Example:

```sh
aws ssm put-parameter --name /last-show/jungp/openai_api_key --type SecureString --value "..."
```

After `terraform apply`, copy the `frontend_env` output into a local `.env`
file in the repo root, then restart `npm start`.
