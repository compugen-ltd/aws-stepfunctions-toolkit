# A minimal AWS Lambda container image. The base image ships the Runtime Interface
# Emulator (RIE), so DockerLambdaStrategy can invoke the handler locally over HTTP.
FROM public.ecr.aws/lambda/python:3.13

COPY app.py ${LAMBDA_TASK_ROOT}/

# CMD is the handler entrypoint (<module>.<function>).
CMD ["app.handler"]
