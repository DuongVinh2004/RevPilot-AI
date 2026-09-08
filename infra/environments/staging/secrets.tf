# RevPilot AI — Ephemeral Credentials & Secrets Management
# Conforms to docs/31-adr/ADR-0009-secrets-and-keys.md and INV-SEC-001

resource "aws_secretsmanager_secret" "platform_config" {
  name                    = "revpilot/${var.environment}/platform-credentials"
  description             = "Encrypted operational secrets and credentials broker store"
  kms_key_id              = aws_kms_key.main.arn
  recovery_window_in_days = 7

  tags = {
    Name = "revpilot-${var.environment}-secrets"
  }
}

resource "aws_iam_policy" "secrets_access" {
  name        = "revpilot-${var.environment}-secrets-read-policy"
  description = "Allows ECS tasks to read RevPilot runtime secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Effect   = "Allow"
        Resource = aws_secretsmanager_secret.platform_config.arn
      },
      {
        Action = [
          "kms:Decrypt"
        ]
        Effect   = "Allow"
        Resource = aws_kms_key.main.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "api_secrets" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.secrets_access.arn
}
