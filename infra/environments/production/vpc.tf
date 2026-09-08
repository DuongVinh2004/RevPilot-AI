# RevPilot AI — VPC and Network Zoning Topology
# Conforms to docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md §5
# Strict 3-zone partitioning: Zone 1 (DMZ), Zone 2 (Compute), Zone 3 (Persistence)

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "revpilot-${var.environment}-vpc"
  }
}

# --- Zone 1: DMZ Ingress Subnets ---
resource "aws_subnet" "public_dmz" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = false

  tags = {
    Name = "revpilot-${var.environment}-dmz-subnet-${count.index + 1}"
    Zone = "Zone-1-DMZ-Ingress"
  }
}

# --- Zone 2: Private Compute Subnets ---
resource "aws_subnet" "private_compute" {
  count                   = length(var.compute_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.compute_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = false

  tags = {
    Name = "revpilot-${var.environment}-compute-subnet-${count.index + 1}"
    Zone = "Zone-2-Private-Compute"
  }
}

# --- Zone 3: Isolated Persistence Subnets ---
resource "aws_subnet" "isolated_persistence" {
  count                   = length(var.persistence_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.persistence_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = false

  tags = {
    Name = "revpilot-${var.environment}-persistence-subnet-${count.index + 1}"
    Zone = "Zone-3-Isolated-Persistence"
  }
}

# --- Routing Tables ---
# 1. Public DMZ Route Table (Isolated internal routing)
resource "aws_route_table" "public_dmz" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "revpilot-${var.environment}-dmz-rt"
  }
}

resource "aws_route_table_association" "public_dmz" {
  count          = length(aws_subnet.public_dmz)
  subnet_id      = aws_subnet.public_dmz[count.index].id
  route_table_id = aws_route_table.public_dmz.id
}

# 2. Private Compute Route Table
resource "aws_route_table" "private_compute" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "revpilot-${var.environment}-compute-rt"
  }
}

resource "aws_route_table_association" "private_compute" {
  count          = length(aws_subnet.private_compute)
  subnet_id      = aws_subnet.private_compute[count.index].id
  route_table_id = aws_route_table.private_compute.id
}

# 3. Isolated Persistence Route Table (Strictly NO External Egress)
resource "aws_route_table" "isolated_persistence" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "revpilot-${var.environment}-persistence-rt"
    Zone = "Zone-3-Isolated-Persistence"
  }
}

resource "aws_route_table_association" "isolated_persistence" {
  count          = length(aws_subnet.isolated_persistence)
  subnet_id      = aws_subnet.isolated_persistence[count.index].id
  route_table_id = aws_route_table.isolated_persistence.id
}
