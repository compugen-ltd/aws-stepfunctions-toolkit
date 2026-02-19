group "default" {
  targets = ["example_batch_1", "example_batch_2", "example_lambda_1"]
}

variable "BASE_DIR" {
  default = "."
}

target "example_batch_1" {
  context = "${BASE_DIR}/project_file/example_batch_1"
  tags = ["example_batch_1:latest"]
}

target "example_batch_2" {
  context = "${BASE_DIR}/project_file/example_batch_2"
  tags = ["example_batch_2:latest"]
}


target "example_lambda_1" {
  context = "${BASE_DIR}/project_file/example_lambda_1"
  tags = ["example_lambda_1:latest"]
}

