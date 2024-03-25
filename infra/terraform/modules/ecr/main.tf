variable "services" {
  description = "A list of microservices to create ECR repositories for"
  type        = list(string)
}

resource "aws_ecr_repository" "service" {
  for_each = toset(var.services)

  name                 = each.value
  image_tag_mutability = "MUTABLE"
}

output "repositories" {
  value = { for k, v in aws_ecr_repository.service : k => v.repository_url }
}
