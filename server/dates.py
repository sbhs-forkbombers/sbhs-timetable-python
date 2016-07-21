from calendar import MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY
from datetime import datetime
from dateutil.relativedelta import relativedelta

default_bells = {
    MONDAY: "[{'bell':'Roll Call','time':'09:00'},{'bell':'1','time':'09:05'},{'bell':'Transition','time':'10:05'},{'bell':'2','time':'10:10'},{'bell':'Lunch 1','time':'11:10'},{'bell':'Lunch 2','time':'11:30'},{'bell':'3','time':'11:50'},{'bell':'Transition','time':'12:50'},{'bell':'4','time':'12:55'},{'bell':'Recess','time':'13:55'},{'bell':'5','time':'14:15'},{'bell':'End of Day','time':'15:15'}]",
    WEDNESDAY: "[{'bell':'Roll Call','time':'09:00'},{'bell':'1','time':'09:05'},{'bell':'Transition','time':'10:05'},{'bell':'2','time':'10:10'},{'bell':'Recess','time':'11:10'},{'bell':'3','time':'11:30'},{'bell':'Lunch 1','time':'12:30'},{'bell':'Lunch 2','time':'12:50'},{'bell':'4','time':'13:10'},{'bell':'Transition','time':'14:10'},{'bell':'5','time':'14:15'},{'bell':'End of Day','time':'15:15'}]",
    FRIDAY: "[{'bell':'Roll Call','time':'09:25'},{'bell':'1','time':'09:30'},{'bell':'Transition','time':'10:25'},{'bell':'2','time':'10:30'},{'bell':'Recess','time':'11:25'},{'bell':'3','time':'11:45'},{'bell':'Lunch 1','time':'12:40'},{'bell':'Lunch 2','time':'13:00'},{'bell':'4','time':'13:20'},{'bell':'Transition','time':'14:15'},{'bell':'5','time':'14:20'},{'bell':'End of Day','time':'15:15'}]"
}

default_bells[TUESDAY] = default_bells[MONDAY]
default_bells[THURSDAY] = default_bells[WEDNESDAY]
default_bells['mon'] = default_bells['tue'] = [
    {'bell':'Roll Call','time':'09:00'},{'bell':'1','time':'09:05'},{'bell':'Transition','time':'10:05'},{'bell':'2','time':'10:10'},
    {'bell':'Lunch 1','time':'11:10'},{'bell':'Lunch 2','time':'11:30'},{'bell':'3','time':'11:50'},{'bell':'Transition','time':'12:50'},
    {'bell':'4','time':'12:55'},{'bell':'Recess','time':'13:55'},{'bell':'5','time':'14:15'},{'bell':'End of Day','time':'15:15'}
]
default_bells['thu'] = default_bells['wed'] = [
    {'bell':'Roll Call','time':'09:00'},{'bell':'1','time':'09:05'},{'bell':'Transition','time':'10:05'},{'bell':'2','time':'10:10'},
    {'bell':'Recess','time':'11:10'},{'bell':'3','time':'11:30'},{'bell':'Lunch 1','time':'12:30'},{'bell':'Lunch 2','time':'12:50'},
    {'bell':'4','time':'13:10'},{'bell':'Transition','time':'14:10'},{'bell':'5','time':'14:15'},{'bell':'End of Day','time':'15:15'}
]
default_bells['fri'] = [
    {'bell':'Roll Call','time':'09:25'},{'bell':'1','time':'09:30'},{'bell':'Transition','time':'10:25'},{'bell':'2','time':'10:30'},
    {'bell':'Recess','time':'11:25'},{'bell':'3','time':'11:45'},{'bell':'Lunch 1','time':'12:40'},{'bell':'Lunch 2','time':'13:00'},
    {'bell':'4','time':'13:20'},{'bell':'Transition','time':'14:15'},{'bell':'5','time':'14:20'},{'bell':'End of Day','time':'15:15'}
]


def getNextSchoolDay():
    now = datetime.now()
    if (now.hour < 15 or (now.hour == 15 and now.hour < 15)) and now.weekday() < SATURDAY:
        return now+relativedelta(hour=0,minute=0,second=0)
    elif now.weekday() >= FRIDAY:
        return now+relativedelta(hour=0,minute=0,second=0,weekday=MONDAY)
    else:
        return now+relativedelta(hour=0,minute=0,second=0,days=1)

def find_next_event(app):
    terms = app.terms
    for i in ['1', '2', '3', '4']:
        (year, month, day) = map(int, terms[i]['start']['date'].split('-'))
        dt = datetime(year, month=month, day=day, hour=9, minute=5)
        if dt > datetime.now():
            app.next_event = dt
            app.inTerm = False
            app.next_event_data = {
                'term': i,
                'end': 0
            }
            break
        (year, month, day) = map(int, terms[i]['end']['date'].split('-'))
        dt = datetime(year, month=month, day=day, hour=15, minute=15)
        if dt > datetime.now():
            app.next_event = dt
            app.next_event_data = {
                'term': i,
                'end': 1
            }
            app.inTerm = True
            break
