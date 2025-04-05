FROM node:14-alpine3.15
COPY . /app
WORKDIR /app
CMD node app.js