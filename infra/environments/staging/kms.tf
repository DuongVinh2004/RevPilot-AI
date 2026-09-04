# RevPilot AI — Customer Managed KMS Key (CMK)
# Conforms to docs/31-adr/ADR-0009-secrets-and-keys.md and INV-SEC-001

resource "aws_kms_key" "main" {
  description             = "Customer managed cryptographic key for RevPilot ${var.environment} encryption at rest"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name = "revpilot-${var.environment}-cmk"
  }
}

resource "aws_kms_alias" "main" {
  name          = "alias/revpilot-${var.environment}-cmk"
  target_key_id = aws_kms_key.main.key_id
}
