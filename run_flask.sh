#!/bin/bash

source ~/.bashrc

export FLASK_APP=mainBrain.py
export FLASK_DEBUG=1

#python mainBrain.py
flask run --host=0.0.0.0


