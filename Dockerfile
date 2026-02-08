FROM mambaorg/micromamba:1.5.8-jammy

WORKDIR /app

# pythonocc-core is provided via conda-forge.
RUN micromamba install -y -n base -c conda-forge \
    python=3.10 \
    pip \
    pythonocc-core \
    && micromamba clean --all --yes

COPY . /app

RUN pip install --no-cache-dir .

ENTRYPOINT ["gml2step"]

