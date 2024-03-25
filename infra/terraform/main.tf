module "vpc" {
  source = "./modules/vpc"
}

module "ecr" {
  source = "./modules/ecr"
  services = ["app"]
}

module "ecs" {
  source = "./modules/ecs"
  vpc_id = module.vpc.vpc_id
  services = ["app"]
  ecr_repositories = module.ecr.repositories
}
