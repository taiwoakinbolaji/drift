# Optional Security Group Module
# Creates a managed Security Group with baseline rules
# This is an EXAMPLE - you can use your existing Security Group instead

resource "aws_security_group" "managed" {
  name        = "${var.project_name}-managed-sg-${var.environment}"
  description = "Managed Security Group with baseline rules for drift detection"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name      = "${var.project_name}-managed-sg-${var.environment}"
      ManagedBy = "Terraform"
      Baseline  = "true"
    }
  )
}

# Baseline Ingress Rule: SSH from specific CIDR
# CUSTOMIZE: Change var.baseline_ssh_cidr to your IP address or remove this rule
resource "aws_vpc_security_group_ingress_rule" "ssh" {
  security_group_id = aws_security_group.managed.id
  description       = "Allow SSH from specific CIDR (baseline)"

  cidr_ipv4   = var.baseline_ssh_cidr
  from_port   = 22
  to_port     = 22
  ip_protocol = "tcp"

  tags = {
    Name     = "ssh-baseline"
    Baseline = "true"
  }
}

# Baseline Ingress Rule: HTTPS from anywhere
# CUSTOMIZE: Set enable_https_baseline to false if not needed
resource "aws_vpc_security_group_ingress_rule" "https" {
  count             = var.enable_https_baseline ? 1 : 0
  security_group_id = aws_security_group.managed.id
  description       = "Allow HTTPS from anywhere (baseline)"

  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 443
  to_port     = 443
  ip_protocol = "tcp"

  tags = {
    Name     = "https-baseline"
    Baseline = "true"
  }
}

# Baseline Egress Rule: Allow all outbound traffic
# CUSTOMIZE: Restrict this if needed based on your security requirements
resource "aws_vpc_security_group_egress_rule" "all_outbound" {
  security_group_id = aws_security_group.managed.id
  description       = "Allow all outbound traffic (baseline)"

  cidr_ipv4   = "0.0.0.0/0"
  ip_protocol = "-1"

  tags = {
    Name     = "all-outbound-baseline"
    Baseline = "true"
  }
}
