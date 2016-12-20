#!/usr/bin/env python
import yaml
import os
config = os.path.join(os.path.dirname(__file__), "testconfig.yaml")
with open(config,'rt') as f:
	conf = yaml.load(f)
