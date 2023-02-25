import numpy as np
import time
import rich
import rich.live
import rich.progress
import rich.layout
from rich import print
import keyboard
from enum import Enum, auto
import collections 
import typing
import json
import pyvis

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

def perror(str):
    print(f"[red]{str}")

def perrort(tag, str):
    print(f"\\[{tag}\\]: [red]{str}")

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
mood_loss = -1/(5*one_hour)

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
    def __init__(self):
        self.time = 0
        self.costs = array([0.0] * needs.count.value)
        self.reqs = {}

    def can_perform(self, agent):
        for k,v in self.reqs.items():
            if k in agent.predicates:
                if agent.predicates[k] != v:
                    return 0
                continue

req_templates = {}
action_templates = {}

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

    def collect_costs(self):
        costs = array([0.0] * needs.count.value)
        for action in self.actions:
            costs += action.costs
        return costs

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



    def __str__(self): return f"Agent[{self.name}]"
    def __repr__(self): return self.__str__()

agent_templates = {}


# ----------------------------------------------------------------------------------------------------------------------------------------------------
#      @functions
# ----------------------------------------------------------------------------------------------------------------------------------------------------

agents = []

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

# loads data into a given obj from a template
def load_object_from_template(name):
    def error(str):
        perrort("load_object_from_template", f"while loading from template '{name}': {str}")

    if name not in object_templates:
        error(f"{name} has no object template")
        return

    o = object_templates[name]
    obj = Object()
    obj.adverts = o.adverts
    obj.predicates = o.predicates
    return obj

def load_agent_from_template(name):
    def error(str):
        perrort("load_agent_from_template", f"while loading from template '{name}': {str}")

    if name not in agent_templates:
        error(f"{name} has no agent template")
        return
    
    o = agent_templates[name]
    obj = Agent()
    obj.adverts = o.adverts
    obj.predicates = o.predicates
    return obj
 

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

def load_requirement_templates(ontology):
    req_templates = ontology['templates']['reqs']


def load_concepts(ontology:dict):
    # we have to load all concepts in first, because they reference each other
    for concept in ontology["concepts"]:
        if concept in concepts: 
            perrort("concept loading", f"Duplicate concept {concept}.")
            return
        concepts[concept] = Concept()
        
    for con,attributes in ontology["concepts"].items():
        concept = concepts[con]
        concept.name = con
        for attribute,value in attributes.items():

            if attribute in concept.predicates:
                perrort("concept loading", f"Duplicate attribute '{attribute}'. If you want to define multiple values for an attribute, use an array.")
                continue

            if attribute == 'desc':
                if type(value) != str:
                    perrort("concept loading", f"Invalid value for 'desc' on '{concept}', must be a string.")
                concept.desc = value

            if attribute == 'subclass of' or attribute == 'instance of':
                if type(value) == list:
                    concept.predicates[attribute] = []
                    for element in value:
                        if element not in concepts:
                            perrort("concept loading", f"The concept '{element}' was not defined, but it is referenced by '{concept}'.")
                            continue
                        concept.predicates[attribute].append(concepts[element])
                elif type(value) == str:
                    if value not in concepts:
                        perrort("concept loading", f"The concept '{value}' was not defined, but it is referenced by '{concept}'.")
                    else: concept.predicates[attribute] = concepts[value]
                else: perrort("concept loading", f"Invald value for attribute '{attribute}' on '{concept}', must be either a string or an array of strings.")

            if attribute == 'part of':
                if type(value) == list:
                    concept.predicates['part of'] = []
                    for element in value:
                        if element not in concepts:
                            perrort("concept loading", f"The concept '{element}' was not defined, but it is referenced by '{concept}'.")
                            continue
                        concept.predicates['part of'].append(concepts[element])
                elif type(value) == str:
                    if value not in concepts:
                        perrort("concept loading", f"The concept '{value}' was not defined, but it is referenced by '{concept}'.")
                    else: concept.predicates['part of'] = value
                else: perrort("concept loading", f"Invald value for attribute 'part of' on '{concept}', must be either a string or an array of strings.")

            if attribute == 'has quality':
                if type(value) == list:
                    concept.predicates['has quality'] = []
                    for element in value:
                        concept.predicates['has quality'].append(element)

# walks up the tree to see if this concept can be considered an agent, eg. is it or any of its inherited 
# concepts a subclass of animal. this method really sucks, probably just store a variable 
# indicating this on any concept, since it's such an important distinction
def concept_is_agent(obj):
    if "instance of" in obj.predicates:
        if type(obj.predicates['instance of']) == list:
            for parent in obj.predicates['instance of'].values():
                if concept_is_agent(parent): return 1
        if concept_is_agent(obj.predicates['instance of']): return 1
    if "subclass of" in obj.predicates:
        if type(obj.predicates['subclass of']) == list:
            for parent in obj.predicates['subclass of'].values():
                if concept_is_agent(parent): return 1
        if concept_is_agent(obj.predicates['subclass of']): return 1
    return 0

# returns whether or not the given string represents any concept
def is_concept(name):
    if name in concepts:
        return 1
    else:
        return 0

# TODO implement actions being concepts somehow
def load_action_templates(ontology):
    actions = ontology['templates']['actions']

    working_action = ""

    def error(str):
        perrort("action template loader", f"while loading '{working_action}' template: {str}")

    for a, data in actions.items():
        working_action = a
        action = Action()
        action.name = a

        def load_time(times):
            t = 0
            for time,value in times.items():
                if   time == 'seconds': t += value * one_second
                elif time == 'minutes': t += value * one_minute
                elif time == 'hours':   t += value * one_hour
                elif time == 'days':    t += value * one_day
                elif time == 'months':  t += value * one_month
                elif time == 'years':   t += value * one_year
            return t

        for attribute, value in data.items():
            if attribute == 'time':
                action.time = load_time(value)
            elif attribute == 'reqs':
                if type(value) == str:
                    # the action must want to load the reqs defined for a certain concept
                    if value not in req_templates: error(f"there is no req template specified for the concept '{value}'"); continue
                    action.reqs = req_templates[value]
                elif type(value) == dict:
                    action.reqs = value # no saftey checking is done here, if something is wrong it wont be exposed until later
                else: error(f"invalid value for 'reqs'"); continue

def load_object_templates(ontology):
    templates = ontology['templates']['objects']

    working_object = ""

    def error(str):
        perrort("object template loader", f"while loading '{working_object}' template: {str}")

    for o, data in templates.items():
        working_object = o
        if not is_concept(o):
            error(f"The name '{o}' does not belong to any loaded concept.")
            continue
        object_templates[o] = Object()
        object : Object = object_templates[o]
        object.age = 0
        object.mass = 0
        object.pos = (0,0)
        object.name = o
        object.predicates['instance of'] = concepts[o]

        def load_time(times):
            t = 0
            for time,value in times.items():
                if   time == 'seconds': t += value * one_second
                elif time == 'minutes': t += value * one_minute
                elif time == 'hours':   t += value * one_hour
                elif time == 'days':    t += value * one_day
                elif time == 'months':  t += value * one_month
                elif time == 'years':   t += value * one_year
            return t

        def load_action(action):
            out = Action()
            for attr, data in action.items():
                if attr == 'time':
                    out.time = load_time(data)
                elif attr == 'costs':
                    for cost,value in data.items():
                        if   cost == 'food':    out.costs[needs.food.value] = value
                        elif cost == 'mood':    out.costs[needs.mood.value] = value
                        elif cost == 'sleep':   out.costs[needs.sleep.value] = value
                        elif cost == 'bladder': out.costs[needs.bladder.value] = value
                elif attr == 'reqs':
                    out.reqs = data
            return out

        def load_actions(actions):
            return # TODO implement multiple actions
            out = []
            for act, data in actions.items():
                action = Action()
                action.name = act
                if type(data) == str: # here we assume that the user wants the action to just be one defined in action templates
                    if data not in action_templates:
                        error("Attempted to load action '{data}' as a template, but no template is defined for this name.")
                        continue
                elif type(data) == dict:
                    pass  
                else: error("invalid data type for action"); continue

        def load_adverts(adverts):
            out = []
            for ad, data in adverts.items():
                advert = Advert()
                advert.name = ad
                for attribute, value in data.items():
                    if attribute == 'action':
                        advert.actions.append(load_action(value))
                    elif attribute == 'actions':
                        advert.actions = load_actions(value)
                out.append(advert)
            return out

        for attribute,value in data.items():
            if attribute == 'adverts':
                object.adverts = load_adverts(value)

def load_agent_templates(ontology):
    templates = ontology['templates']['agents']

    working_agent = ""

    def error(str):
        perrort("object template loader", f"while loading '{working_agent}' template: {str}")

    for a,data in templates.items():
        working_agent = a
        if not is_concept(a):
            error(f"The name '{a}' does not belong to any loaded concept.")
            continue
        agent_templates[a] = Agent()
        agent = agent_templates[a]

        def load_predicates(predicates):
            out = {}
            for predicate,data in predicates.items():
                if predicate == 'has':
                    if type(data) == None:
                        out['has'] = None
                    elif type(data) == dict:
                        out['has'] = {}
                        for name,value in data.items():
                            out['has'][name] = {}
                            if type(value) == str:
                                if value.startswith("object"):
                                    n = value[7:-1]
                                    if not is_concept(n):
                                        error(f"'{n}' is not a concept.")
                                        continue
                                    if n not in object_templates:
                                        error(f"there is no object template for '{n}'.")
                                        continue
                                    out['has'][name] = load_object_from_template(n)
            return out

        for attribute,value in data.items():
            if attribute == 'predicates':
                agent.predicates = load_predicates(value)

def load_ontology():
    global object_templates
    f = open("misc/agent_modeling/ontology.json")
    ontology = json.load(f)    
    f.close()

    load_concepts(ontology)
    # load_requirement_templates(ontology)
    # load_action_templates(ontology)
    load_object_templates(ontology)
    load_agent_templates(ontology)


def agent_tick(agent:Agent):
    def score_advert(advert:Advert, obj:Object):
        narr = agent.needs
        aarr = advert.collect_costs()
        scores = aarr/(aarr*(aarr+narr)+1e-8)
        return np.mean(scores)/mag_squared(agent.pos-obj.pos)

    def perform_queue():
        if len(agent.action_queue):
            curr:tuple[Action,int] = agent.action_queue[0]
            if not curr[1]:
                agent.action_queue.pop(0)
                print(f"Agent {agent} moves onto {agent.action_queue[0][0]}")
            else: curr[1] -= 1
            if len(agent.action_queue): return 1
        return 0

    if perform_queue(): return

    adlist = []
    for object in objects:
        for advert in object.adverts:
            adlist.append((advert,object))

    max,i = 0,0
    for j,(advert,object) in enumerate(adlist):
        v = score_advert(advert, object)
        if v > max: max,i = v,j
    for action in adlist[i][0].actions:
        agent.action_queue.insert(0, (action, action.time))
    
    perform_queue()


load_ontology()

agent:Agent = load_agent_from_template("human") 
agent.name = "Noe"
agent.age = 20*one_year
agent.pos = array([3,2])
agents.append(agent)

object:Object = load_object_from_template("apple") # type:ignore
object.name = "apple"
object.pos = array([1,2])
objects.append(object)

print(agent.predicates)

while 1:
    for agent in agents:
        agent_tick(agent)


