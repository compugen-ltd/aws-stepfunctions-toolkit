group "default" {
  targets = ["awsbatch", "lambda"]
}

variable "BASE_DIR" {
  default = "."
}

target "example_batch_1" {
  context = "${BASE_DIR}/aws_batch/example_batch_1"
  tags = ["example_batch_1:latest"]
}

target "example_batch_2" {
  context = "${BASE_DIR}/aws_batch/example_batch_2"
  tags = ["example_batch_2:latest"]
}


target "example_lambda_1" {
  context = "${BASE_DIR}/functions/example_lambda_1"
  tags = ["example_lambda_1:latest"]
}

