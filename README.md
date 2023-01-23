# Priotask
Priotask helps manage and prioritize tasks for effective time management, allowing users to quickly focus on important tasks and meet deadlines. It streamlines manual workload management.

## The Behaviour
Priotask is supposed to let a user register the tasks they need to do and help them schedule them. The user can also prioritize tasks, and the application will help them focus on the most important tasks. The user can also mark tasks as done, and the application will adapt to the user's preferences. 
## The Code Behind
The project is a client-server application. The server is suppose to store user and task data, while the client is the user interface for the aplication. All the code is written in Python. The server includes a database, which is a SQLite database. The server also includes a 'Prioritizer'. This prioritizer is a small neural network that is trained to prioritize tasks based on the user's input. That is, each time a user selects to do a task, that one is flagged to be the priority and the prioritizer is adapted to consider those parameters as important. The idea is that each user will have their own prioritizer, which will be trained to prioritize tasks based on their own preferences. (This means that the neural network's weights will be stored in the database, and will be updated each time the user selects a task to do.)
## The Future
The first version of Priotask will be fully Python based, but this does not necessarilly be the case later on. The idea is to support mobile devices with a client application (at least on Android). 
## The Team
The project is developed by Danel Arias, a student at the University of Deusto, in Bilbao, Spain.

## The TODO List
This section presents all the tasks that need to be done to complete the project.
### Server
- [ ] Create the server storage system through a sqlite3 database
- [ ] Create the server prioritizer as a neural network
- [ ] Create the server user management system
- [ ] Create the server task management system
- [ ] Create the server API
### Client
- [ ] Create the client user interface
- [ ] Create the client task management system
- [ ] Create the client connection to the server
### Tests
- [ ] Create the tests for the server
- [ ] Create the tests for the client
### Documentation
- [ ] Create the documentation for the server
- [ ] Create the documentation for the client
### Other
- [ ] Create the installation script
- [ ] Create the uninstallation script
- [ ] Create the update script

 
