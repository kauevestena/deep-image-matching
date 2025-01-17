FROM pytorch/pytorch:latest

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update
RUN apt install -y git

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

RUN pip install git+https://github.com/3DOM-FBK/deep-image-matching.git
RUN pip install pycolmap

# Clone repo
RUN git clone https://github.com/3DOM-FBK/deep-image-matching.git /workspace/deep-image-matching
WORKDIR /workspace/deep-image-matching

# Running the tests:
RUN pytest