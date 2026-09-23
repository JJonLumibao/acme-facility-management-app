resource "random_id" "this" {
  byte_length = 4

  keepers = {
    seed_input = try(var.aws_app_code, terraform.workspace)
  }
}

resource "random_pet" "this" {
  length    = 3
  separator = "-"

  keepers = {
    seed_input = try(var.aws_app_code, terraform.workspace)
  }
}

# Signing key for the backend's JWT access/refresh tokens (read as JWT_SECRET by backend/api/auth/security.py).
resource "random_password" "jwt" {
  length  = 48
  special = false
}

# Password for the demo accounts seeded into the cloud database (backend/api/seed.py reads DEMO_PASSWORD).
resource "random_password" "demo" {
  length  = 16
  special = false
}
