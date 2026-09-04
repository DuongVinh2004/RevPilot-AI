# RevPilot AI — Application Load Balancer (Zone 1 DMZ Ingress)
# Conforms to docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md §5.1 and §6

resource "aws_lb" "api" {
  name               = "revpilot-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public_dmz[*].id

  drop_invalid_header_fields = true
  enable_deletion_protection = false

  tags = {
    Name = "revpilot-${var.environment}-alb"
    Zone = "Zone-1-DMZ-Ingress"
  }
}

resource "aws_lb_target_group" "api" {
  name        = "revpilot-${var.environment}-api-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/health/live"
    port                = "8000"
    protocol            = "HTTP"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
    matcher             = "200"
  }

  tags = {
    Name = "revpilot-${var.environment}-api-tg"
  }
}

# Staging self-signed certificate for TLS termination
resource "aws_acm_certificate" "staging_tls" {
  domain_name       = "staging.revpilot.internal"
  validation_method = "DNS"

  tags = {
    Name = "revpilot-${var.environment}-tls-cert"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.staging_tls.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}
