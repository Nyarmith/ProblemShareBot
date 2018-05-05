#!/usr/bin/python3

import pickle
import telepot
import os
import yaml
import random
import re
import pdb

"""
ProblemShareBot, a bot for sharing problems on a specific group chat.

TODO:
    * Implement more advanced query for ProblemList object
    * Implement max limit to printing problems at once
    * Use database instead of pickling
    * Add remove feature, but make the user have to confirm it
"""

class Problem(object):
    """ fundamental object representing a problem """
    def __init__(self, title, URL, diff, TAGS):
        self.title      = title
        self.URL        = URL
        self.difficulty = diff
        self.tags       = set(TAGS)
        self.id         = None
    def __str__(self):
        return '{}(#{})'.format(self.title, self.id)

class ProblemList(object):
    """ Keeps track of problems done by each user """
    def __init__(self):
        self.problems       = {}
        self.users          = {}
        self.userNameMap    = {}
        self.free_ids    = set()

    def Add(self, prob):
        """ Add a new problem object the list, creating a unique id """
        if prob.title in self.problems:
            raise Exception('Problem with same title already exists')

        #check previously used ids
        if len(self.free_ids) > 0:
            prob.id = str(self.free_ids.pop())
        else:
            prob.id = str(len(self.problems))

        #map both to same problem
        self.problems[prob.id]    = prob
        self.problems[prob.title] = prob

    def Remove(self, title_or_id):
        """ Remove a problem by id or title from the problem list """
        if title_or_id not in self.problems:
            raise Exception('Problem does not exist')

        #get problem object from one key to remove both
        prob = self.problems[title_or_id]
        del self.problems[prob.id]
        del self.problems[prob.title]

        #remove problem from user's profiles
        for usr in self.users:
            if prob.id in self.users[usr]:
                del self.users[usr][prob.id]

        #make id available again
        self.free_ids.add(prob.id)

    def Mark(self, user, title_or_id):
        """ Mark a problem for a particular user as done """
        uid  = user['id']
        name = user['first_name']
        #Add user if unknown
        if uid not in self.users:
            self.users[uid]       = {}
            self.userNameMap[uid] = name
        if title_or_id not in self.problems:
            raise Exception('Problem does not exist')

        #mark as done for that user, by id
        p = self.problems[title_or_id]
        self.users[uid][p.id] = 'done' #this can be extended to other states

    def GetProb(self, title_or_id):
        """ Get problem from numeric id(as string) or title identifier """
        if title_or_id not in self.problems:
            raise Exception('Problem does not exist')
        else:
            return self.problems[title_or_id]

    def GetRandProb(self):
        """ Choose completely random problem """
        return random.choice(list(self.problems.values()))

    def QueryProbs(self, s): #if s appears in title, difficulty, or tags then add to return list
        """ Find all problems containing string s in their properties"""
        s = s.lower()
        retlist = []
        for p in set(self.problems.values()):
            #check title
            if s in p.title.lower() or s in p.difficulty.lower() or any(s in tag.lower() for tag in p.tags):
                retlist.append(p)
        return retlist

def ProblemFromStr(s):
    """
    Expected Problem Format:
        <URL> [title] [difficulty] [tags]
        e.g. 
        http://codeforces.com/problemset/problem/298/B [sail] [medium] [greedy]
    """
    params = re.findall(r'\[\w*\]',s)
    if (len(params) != 3):
        raise Exception('Invalid Syntax, format: URL [title] [difficulty] [tags]\nSquare brackets required')
    else:
        return Problem(params[0][1:-1].strip(), s.split()[0].strip(), 
            params[1][1:-1].strip(), [tag.strip() for tag in params[2][1:-1].split(',')] )

#arg : ProblemList
def makeScoreBoard(pl):
    rsp = ''
    for usr in pl.users:
        rsp += '<a href=\"tg://usr?id={}\">@{}</a>: \n'.format(usr,pl.userNameMap[usr])
        for prob in pl.users[usr]:
            rsp +=  '  ' + str(pl.GetProb(prob))
    return rsp

#arg: Problem()
def fmtProblem(p):
    return '<a href=\"{0}\">{0}</a><pre>Title : {1}\nDifficulty : {2}\nTags : {3}</pre>' \
            .format(p.URL, p.title, p.difficulty, '.'.join(p.tags))

#arg: [Problem(), Problem(), ...]
def fmtProblems(l):
    rsp = ''
    for p in l:
        rsp += fmtProblem(p)
        rsp += '\n'
    return rsp


class ProblemShareBot(object):
    def __init__(self):
        """ Declare members """
        self.problems = ProblemList()

    def start(self, args):
        """ Lets the bot work in a chat """
        return "Bot enabled for chat"

    def add(self, args):
        """ Prompts dialog to add a new bot """
        p = ProblemFromStr(args.message)
        self.problems.Add(p)
        return 'Problem added, id: {}'.format(p.id)

    def mark(self, args):
        """ Mark a problem as completed """
        if args.message.strip() == '':
            return 'No problem specified!'
        self.problems.Mark(args.fromusr, args.message.strip())
        p = self.problems.GetProb(args.message.strip())
        return 'Problem {} marked by user <a href=\"tg://usr?id={}\">@{}</a>\n' \
                .format(p.id, args.fromusr['id'], args.fromusr['first_name'])

    def scoreboard(self, args):
        """ Lists scoreboard of completed problems for the chat """
        return makeScoreBoard(self.problems)

    def random(self, args):
        """ Get a random problem with optional filters """
        p = self.problems.GetRandProb()
        return fmtProblem(p)

    def query(self, args):
        """ Given filters list matching problems """
        probs = self.problems.QueryProbs(args.message.strip())
        return fmtProblems(probs)

    def help(self, args):
        """ Gives help for bot usage """
        return """
        Problem-Share-Bot:
/add  : Add new problem.\n    Expected format: URL [title] [tags] [difficulty]
/mark : Mark a problem as completed.\n    Expected Format : [problem_title | problem_id]
/scoreboard : Print chat scoreboard
/random : Get a random problem.
/query : Get a list of problems based on a filter
        """



class botArg(object):
    """formatted bot argument"""
    def __init__(self, fromusr, message):
        self.fromusr = fromusr
        self.message = message


if __name__ == '__main__':
    #load config
    f = open('config.yml')
    cfgstr = f.read()
    mykey    = yaml.load(cfgstr)['key']
    savefile = yaml.load(cfgstr)['save']
    f.close()
    
    #load save or initialize new bot
    PB = None
    if os.path.exists(savefile):
        with open(savefile,'rb') as f:
            PB = pickle.load(f)
    else:
        PB = ProblemShareBot()
    
    
    def handle(msg):
        chat_id = msg['chat']['id']
        command = msg['text']
        fromusr = msg['from']  #is a dict of 'first_name' : <users first name>, 'id' : <users id>
    
        print("got command: {}".format(command))
    
        split_msg = command.split()
        m = re.match(r'\s*/\S+\b', command);
        method    = m.group().strip()[1:].split('@')[0]
    
        ind = m.span()[1]+1
        msgstr = command[ind:]

        arg = botArg(fromusr,msgstr.strip())

        rsp = 'Unpopulated'
        try:
            rsp = getattr(PB, method)(arg)
        except Exception as ex:
            rsp = str(ex)

        bot.sendMessage(chat_id, rsp, parse_mode='html')
    
        with open(savefile,'wb') as f:
            pickle.dump(PB, f, pickle.HIGHEST_PROTOCOL)
    
    
    #initialize the bot as a global that everything relies on
    bot = telepot.Bot(mykey)
    
    print("i'm listening yo")
    bot.message_loop(handle, run_forever=True)

