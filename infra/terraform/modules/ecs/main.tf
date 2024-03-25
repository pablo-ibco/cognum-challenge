variable "vpc_id" {
  description = "The VPC ID to launch the ECS service in"
}

variable "services" {
  description = "A list of microservices to create ECS services for"
  type        = list(string)
}

variable "ecr_repositories" {
  description = "A map of ECR repository URLs keyed by service name"
  type        = map(string)
}

resource "aws_ecs_cluster" "main" {
  name = "microservices-cluster"
}

resource "aws_ecs_task_definition" "service" {
  for_each = toset(var.services)

  family                   = each.value
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  container_definitions    = jsonencode([
    {
      name      = each.value
      image     = var.ecr_repositories[each.value]
      cpu       = 256
      memory    = 512
      essential = true
      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
        }
      ]
    }
  ])
}

resource "aws_iam_role" "ecs_task_execution" {
  name = "ecs_task_execution_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Effect = "Allow"
        Sid    = ""
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
