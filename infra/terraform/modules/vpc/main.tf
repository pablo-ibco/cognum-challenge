resource "aws_vpc" "main" {
  cidr_block           = var.cidr_block
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "MainVPC"
  }
}

variable "cidr_block" {
  description = "The CIDR block for the VPC"
  default     = "10.0.0.0/16"
}

output "vpc_id" {
  value = aws_vpc.main.id
}
