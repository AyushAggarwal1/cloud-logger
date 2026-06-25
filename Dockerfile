FROM python:3.13-slim

WORKDIR /app

# hadolint ignore=DL3008,DL3015,DL3009
RUN apt-get update -y \
    && apt-get install --no-install-recommends -y 
    
COPY . .

RUN pip3 install -r requirements.txt --no-cache-dir

ENTRYPOINT [ "/bin/bash" ]
