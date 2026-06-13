terraform {
  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type    = string
  default = "ca-central-1"
}

variable "ucid" {
  type        = string
  description = "Your UCID. Used to suffix assignment resources."
  default     = "jungp"
}

variable "ssm_parameter_path" {
  type        = string
  description = "Path containing SecureString API keys for OpenAI and Cloudinary."
  default     = null
}

variable "openai_model" {
  type        = string
  description = "OpenAI model used by the create-obituary Lambda."
  default     = "gpt-5.5"
}

variable "polly_voice_id" {
  type        = string
  description = "Amazon Polly voice ID used for obituary narration."
  default     = "Joanna"
}

locals {
  app_name           = "last-show"
  resource_suffix    = var.ucid
  table_name         = "obituaries-${local.resource_suffix}"
  get_function_name  = "get-obituaries-${local.resource_suffix}"
  post_function_name = "create-obituary-${local.resource_suffix}"
  parameter_path     = coalesce(var.ssm_parameter_path, "/last-show/${local.resource_suffix}/")
}

data "archive_file" "get_obituaries" {
  type        = "zip"
  source_file = "${path.module}/../functions/get-obituaries/main.py"
  output_path = "${path.module}/get-obituaries.zip"
}

data "archive_file" "create_obituary" {
  type        = "zip"
  source_file = "${path.module}/../functions/create-obituary/main.py"
  output_path = "${path.module}/create-obituary.zip"
}

resource "aws_dynamodb_table" "obituaries" {
  name           = local.table_name
  billing_mode   = "PROVISIONED"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

resource "aws_iam_role" "lambda_role" {
  name = "last-show-lambda-${local.resource_suffix}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "last-show-lambda-policy-${local.resource_suffix}"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Scan",
          "dynamodb:PutItem"
        ]
        Resource = aws_dynamodb_table.obituaries.arn
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter${local.parameter_path}*"
      },
      {
        Effect = "Allow"
        Action = [
          "polly:SynthesizeSpeech"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "get_obituaries" {
  function_name    = local.get_function_name
  filename         = data.archive_file.get_obituaries.output_path
  source_code_hash = data.archive_file.get_obituaries.output_base64sha256
  role             = aws_iam_role.lambda_role.arn
  handler          = "main.lambda_handler"
  runtime          = "python3.11"
  timeout          = 10

  environment {
    variables = {
      OBITUARIES_TABLE = aws_dynamodb_table.obituaries.name
    }
  }
}

resource "aws_lambda_function" "create_obituary" {
  function_name    = local.post_function_name
  filename         = data.archive_file.create_obituary.output_path
  source_code_hash = data.archive_file.create_obituary.output_base64sha256
  role             = aws_iam_role.lambda_role.arn
  handler          = "main.lambda_handler"
  runtime          = "python3.11"
  timeout          = 20

  environment {
    variables = {
      CLOUDINARY_FOLDER  = local.app_name
      OBITUARIES_TABLE   = aws_dynamodb_table.obituaries.name
      OPENAI_MODEL       = var.openai_model
      POLLY_VOICE_ID     = var.polly_voice_id
      SSM_PARAMETER_PATH = local.parameter_path
    }
  }
}

resource "aws_lambda_function_url" "get_obituaries" {
  function_name      = aws_lambda_function.get_obituaries.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["GET"]
    allow_headers = ["content-type"]
  }
}

resource "aws_lambda_function_url" "create_obituary" {
  function_name      = aws_lambda_function.create_obituary.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["content-type"]
  }
}

resource "aws_lambda_permission" "allow_get_function_url" {
  statement_id           = "AllowPublicFunctionUrlInvoke"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.get_obituaries.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "allow_create_function_url" {
  statement_id           = "AllowPublicFunctionUrlInvoke"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.create_obituary.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

output "get_obituaries_url" {
  value = aws_lambda_function_url.get_obituaries.function_url
}

output "create_obituary_url" {
  value = aws_lambda_function_url.create_obituary.function_url
}

output "frontend_env" {
  value = <<EOT
REACT_APP_GET_OBITUARIES_URL=${aws_lambda_function_url.get_obituaries.function_url}
REACT_APP_CREATE_OBITUARY_URL=${aws_lambda_function_url.create_obituary.function_url}
EOT
}
