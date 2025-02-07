ARG PYTHON_VERSION=3.11
FROM python:$PYTHON_VERSION AS dev

# Set the user and group IDs for the nonroot user
ARG USER_UID=1000
ARG USER_GID=1000

# FIXME: entrypoint not working when moved to USER nonroot
ENTRYPOINT ["/app/boefjes/entrypoint.sh"]

# Create a nonroot group with the specified GID
RUN groupadd --gid "$USER_GID" nonroot
# Create a nonroot user with the specified UID and GID
RUN adduser --disabled-password --gecos '' --uid "$USER_UID" --gid "$USER_GID" nonroot
# Add nonroot user to the docker group
RUN groupadd --force --gid 999 docker && usermod -aG docker nonroot

# Set the working directory
WORKDIR /app/boefjes
ENV PATH=/home/nonroot/.local/bin:${PATH}
ARG ENVIRONMENT

# Copy the requirements files
COPY boefjes/requirements-dev.txt boefjes/requirements.txt .

# Install dependencies
RUN --mount=type=cache,target=/root/.cache \
    pip install --upgrade pip \
    && if [ "$ENVIRONMENT" = "dev" ]; \
    then \
    pip install -r requirements-dev.txt; \
    else \
    pip install -r requirements.txt; \
    fi

FROM dev

# Copy the octopoes directory and build the wheel package
COPY octopoes/ /tmp/octopoes
RUN cd /tmp/octopoes && python setup.py bdist_wheel
# Install the octopoes package
RUN pip install /tmp/octopoes/dist/octopoes*.whl

# Copy the entrypoint script and the boefjes directory
COPY boefjes/entrypoint.sh .
COPY boefjes/boefjes ./boefjes

# Switch to the nonroot user
USER nonroot

CMD ["python", "-m", "bin.worker", "boefje"]
