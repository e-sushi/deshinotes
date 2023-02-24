import numpy as np
import time
import rich
import rich.live
import rich.progress
import rich.layout
import keyboard
from enum import Enum, auto
import collections 
import typing
import json

# ontology data for agent modeling
# this file contains definitions of concepts, adverts, actions, and verbs

# key descriptions:
#
#  desc: 
#      for concepts, this provides a brief description of the concept in question
#  
#  subclass of:
#      this concept is a subset of the specified class, and so is itself a class
#  
#  instance of:  
#      this concept is an instance of the specified class
#      for example, if we have the class 'apple', which contains all apples, 
#      'green apple' is an instance of 'apple'
# 
#  plural:
#      the plural form of the concept's name. not sure if this will be kept
#
#  has quality:
#      a quality or array of qualities that this concept exhibits
#
#  has:
#      when used as a predicate, indicates that the subject has the object. the object 
#      in possession of the subject in someway. for example, a hand uses "has" to indicate
#      that it is holding the object. a container uses "has" to describe what objects are 
#      inside of it

array = np.array

class needs(Enum):
    bladder = auto()
    food    = auto()
    sleep   = auto()
    mood    = auto()
    count   = auto()

class skills(Enum):
    pass

progress = rich.progress.Progress()

need_tasks = []
for k in needs:
    need_tasks.append(progress.add_task(k.name, total=1))

state_task = progress.add_task("")

layout = rich.layout.Layout()
layout.split_column(
    rich.layout.Layout(progress),
    rich.layout.Layout("", name="time")
)

live = rich.live.Live(layout, refresh_per_second=30)
# live.start()

total_time = 0

np.set_printoptions(linewidth=np.inf)

def mag_squared(a:np.ndarray):
    return np.sum(np.square(a))

def clamp(val, min, max):
    if val < min: return min
    if val > max: return max
    return val

one_second = 1
one_minute = one_second * 60
one_hour = one_minute * 60
one_day = one_hour * 24
one_month = one_day * 31
one_year = one_month * 12

one_gram = 1
one_kilogram = 1000*one_gram

sleep_loss = -1/(3*one_day)
food_loss = -1/(6*one_hour)
mood_loss = -1/(5*one_hour)w

def format_time(time):
    if not time: return "0 seconds"
    if time > one_day: 
        n_days = time//one_day
        return f"{n_days} day{'s' if n_days > 1 else ''} {format_time(time-n_days*one_day)}"
    if time > one_hour:
        n_hours = time//one_hour
        return f"{n_hours} hour{'s' if n_hours > 1 else ''} {format_time(time-n_hours*one_hour)}"
    if time > one_minute:
        n_minutes = time//one_minute
        return f"{n_minutes} minute{'s' if n_minutes > 1 else ''} {format_time(time-n_minutes*one_minute)}"
    return f"{time} second{'s' if time > 1 else ''}"

# a need 
class Need:
    def __init__(self, name, value):
        self.name = name
        self.value = value
    
    def d(self,v:float):
        self.value = clamp(self.value + v, 0, 1)

    def __str__(self): return f"Need[{self.name}, {self.value}]"
    def __repr__(self): return self.__str__()

def human_costs(bladder = 0, food = 0, sleep = 0, mood = 0):
    return array([bladder, food, sleep, mood])


# grammar helper
class Verb:
    def __init__(self, infinitive, present, past):
        self.infinitive = infinitive
        self.present_participle = present
        self.past_participle = past


# anything that exists, whether it be physical, abstract, tangible, intangible... so on.
# all things have a name and a set of predicates describing qualities about that thing
class Entity:
    def __init__(self):
        self.name = ""
        self.desc = ""
        self.predicates = {}


# defines a relationship between 2 entities 
# TODO
class Predicate:
    def __init__(self, subject:Entity, predicate:str, object:Entity):
        self.subject   = subject
        self.predicate = predicate
        self.object    = object

# a 'mental' representation about an entity. for example, you have leaves in real life, but 
# you know them all by the same concept that represents them. this is used so that agents
# may store memories about abstract representations about things and don't have to rely
# on an entity existing in reality to think about them.
# im not sure if i need to keep this class around, but i will in case there ever becomes 
# a reason to differenciate it from Entity
class Concept(Entity):
    def __init__(self):
        super().__init__()

    def __str__(self): return f"Concept[{self.name}]"
    def __repr__(self): return self.__str__()

concepts = {} # loaded in by load_ontology()


# an event that is caused by an agent, given to them when chosen through an advert
class Action(Concept):
    def __init__(self, verb:Verb, time:float, costs, reqs:dict):
        self.verbs = verb
        self.time = time
        self.costs = array(costs)
        self.reqs = reqs

    def can_perform(self, agent):
        for k,v in self.reqs.items():
            if k in agent.predicates:
                if agent.predicates[k] != v:
                    return 0
                continue

# represents a advertisement that an object projects to other objects. 
# consists of a series of actions for the agent to undertake
# this is not a part of the ontology, as it's not something that the agents are meant to 
# be conciously aware of (i think)
class Advert:
    def __init__(self):
        self.name = ""
        self.actions = []

    def can_select(self,agent):
        return 1

    def __str__(self): return f"Advert[{self.name}, {self.actions}]"
    def __repr__(self): return self.__str__()

adverts = {}

objects = []

# Entity/Object
# something tangible that may be acted upon. has a position in reality, an age, mass, and a 
# list of adverts animate objects may take against it
class Object(Entity):
    def __init__(self):
        super().__init__()
        self.age     = 0
        self.pos     = array([0,0])
        self.mass    = 0
        self.adverts = []

    @classmethod
    def from_template(cls, name, store = True):
        print(cls)
        if name not in object_templates:
            print(f"The concept '{name}' has no defined template.")
            return None
        template = object_templates[name]
        o = cls()
        o.name = name
        for attribute, value in template.items():
            if attribute == 'predicates':
                for verb,object in value.items():
                    if verb == 'has':
                        o.predicates['has'] = {}
                        if type(object) == dict:
                            for item,val in object.items():
                                if type(val) == str:
                                    if val.startswith("template"):
                                        o.predicates['has'][item] = Object.from_template(val[9:-1])
                        elif object == None:
                            o.predicates['has'] = None
                        else: print(f"Invalid value for 'has' verb found while loading template '{name}'.")
                    else: print(f"Unknown verb '{verb}' found when parsing predicates of template '{name}'.")
            else: print(f"Unknown attribute '{attribute}' found when loading template '{name}'.")
        if store: objects.append(o)
        return o

    def __str__(self): return f"Object[{self.name}]"
    def __repr__(self): return self.__str__()

object_templates = {}

# Entity/Object/Agent
# an animate object that can make decisions to take actions on other objects based on 
# a list of needs and is able to store memories about entities.
class Agent(Object):
    def __init__(self):
        super().__init__()
        self.action_queue : list[tuple[Action,int]] = []# stores a queue of actions as well as the time remaining for that action
        self.needs   = array([1.0] * needs.count.value)
        self.memories = []

    @classmethod
    def from_template(cls, name, store = True):
        print(cls)
        agent = super().from_template(name)
        return agent

    def array(self):
        return np.array([self.needs["bladder"], self.needs["food"], self.needs["sleep"], self.needs["mood"]])

    def val_array(self):
        return np.array([self.needs["bladder"].value, self.needs["food"].value, self.needs["sleep"].value, self.needs["mood"].value])

    def score_advert(self, advert:Advert):
        narr = self.val_array()
        aarr = advert.array()
        scores = aarr/(aarr*(aarr+narr)+1e-8)
        return np.mean(scores)

    def tick(self):
        layout["time"].update(format_time(total_time))
        for i,task in enumerate(need_tasks): progress.update(task, completed=self.needs[i])
        self.needs = np.clip(self.needs + self.action.costs, 0, 1)
        if self.action_time:
            self.action_time = np.max(self.action_time - one_second, 0)
            progress.update(state_task, completed=self.action_time)
            return

        adlist = [a[1] for a in adverts.items()]
        max,i = 0,0
        for j,advert in enumerate(adlist):
            v = self.score_advert(advert)
            if v > max: max,i = v,j
        self.action = adlist[i]
        self.action_time = adlist[i].time
        progress.update(state_task, description=self.action.verb, completed=0, total=self.action_time)
        live.refresh()

    def __str__(self): return f"Agent[{self.name}]"
    def __repr__(self): return self.__str__()

agents = []

def print_predicates(subject:str,preds:dict, level = 2):
    for k,v in preds.items():
        if k == 'has':
            if type(v) == dict:
                for i,j in v.items():
                    print(f"{subject} has {i}.")
                    if type(j) == dict:
                        print_predicates(i, j)
                    elif type(j) == list:
                        for e,l in enumerate(j):
                            if type(l) == dict:
                                print_predicates(f"{i}[{e}]", l)
            elif type(v) == list:
                for l in v:
                    if type(l) == dict: print_predicates(l, v)
            else: print(f"{subject} has {v}")
                        
        elif k == 'is':
            if type(v) == list:
                for l in v:
                    print(f"{subject} is {l}")
            else:
                print(f"{subject} is {v}")

paused = 1

def load_concepts(ontology:dict):
    # we have to load all concepts in first, because they reference each other
    for concept in ontology["concepts"]:
        if concept in concepts: 
            print(f"Duplicate concept {concept}.")
            return
        concepts[concept] = Concept()
        
    for con,attributes in ontology["concepts"].items():
        concept = concepts[con]
        for attribute,value in attributes.items():

            if attribute in concept.predicates:
                print(f"Duplicate attribute '{attribute}'. If you want to define multiple values for an attribute, use an array.")
                continue

            if attribute == 'desc':
                if type(value) != str:
                    print(f"Invalid value for 'desc' on '{concept}', must be a string.")
                concept.desc = value

            if attribute == 'subclass of' or attribute == 'instance of':
                if type(value) == list:
                    concept.predicates[attribute] = []
                    for element in value:
                        if element not in concepts:
                            print(f"The concept '{element}' was not defined, but it is referenced by '{concept}'.")
                            continue
                        concept.predicates[attribute].append(concepts[element])
                elif type(value) == str:
                    if value not in concepts:
                        print(f"The concept '{value}' was not defined, but it is referenced by '{concept}'.")
                    else: concept.predicates[attribute] = concepts[value]
                else: print(f"Invald value for attribute '{attribute}' on '{concept}', must be either a string or an array of strings.")

            if attribute == 'part of':
                if type(value) == list:
                    concept.predicates['part of'] = []
                    for element in value:
                        if element not in concepts:
                            print(f"The concept '{element}' was not defined, but it is referenced by '{concept}'.")
                            continue
                        concept.predicates['part of'].append(concepts[element])
                elif type(value) == str:
                    if value not in concepts:
                        print(f"The concept '{value}' was not defined, but it is referenced by '{concept}'.")
                    else: concept.predicates['part of'] = value
                else: print(f"Invald value for attribute 'part of' on '{concept}', must be either a string or an array of strings.")

            if attribute == 'has quality':
                if type(value) == list:
                    concept.predicates['has quality'] = []
                    for element in value:
                        concept.predicates['has quality'].append(element)
                        

def load_actions(ontology:dict):
    pass

def has_quality(object, quality):
    if 'has quality' in object.predicates and quality in object.predicates['has quality']:
        return 1
    if 'instance of' in object.predicates:
        if type(object.predicates['instance of']) == list:
            for parent in object.predicates['instance of']:
                if has_quality(parent, quality): return 1
        if has_quality(object.predicates['instance of'], quality): return 1
    if 'subclass of' in object.predicates:
        if type(object.predicates['subclass of']) == list:
            for parent in object.predicates['subclass of']:
                if has_quality(parent, quality): return 1
        if has_quality(object.predicates['subclass of'], quality): return 1
    return 0

def load_ontology():
    global object_templates
    f = open("agent_modeling/ontology.json")
    ontology = json.load(f)    
    f.close()

    load_concepts(ontology)
    object_templates = ontology['templates']['objects']
   

load_ontology()


agent:Agent = Agent.from_template("human") # type:ignore
agent.name = "Noe"
agent.age = 20*one_year
agents.append(agent)

object:Object = Object.from_template("apple") # type:ignore


print(agent.predicates)

# while 1: 
#     agent.tick()
#     total_time += 1 


