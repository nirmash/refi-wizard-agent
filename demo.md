**Demo 1: Aquire Embr and create a new app**

* Install Ember CLI and login

  mkdir embr-demo && cd embr-demo
  echo "//npm.pkg.github.com/:_authToken=$(gh auth token)" > .npmrc
  echo "@coreai-microsoft:registry=https://npm.pkg.github.com" >> .npmrc
  sudo npm install @coreai-microsoft/embr-cli
  ./node_modules/.bin/embr --version
* Copilot --yolo
* Create hello world app
* Ask Copilot to deploy to Embr
* Show the app
* Create make a change with a pull request
* Show the pull request being different

**Demo 2: Interact with Embr with VSCode**

* People are telling us that they want to see what's going on in the cloud
* This is why we have the VS Code extenstion
* I go to an Embr project
* Code .
* Login to Embr
* Make a change
* Push to Github
* Show the build happening in the extension
* Show the logs
* Show all my projects
* Show the activities

**Demo 3: End-to-end app**

* Now let's look at a more realistic app
* Show the visualization
* Show the app and do something
* Show the telemerty types
* Show the agent
