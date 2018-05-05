FROM frolvlad/alpine-python3

VOLUME /opt/problemBot/
WORKDIR /opt/problemBot/

RUN pip install telepot pyyaml

ADD ProblemShareBot.py .
ADD config.yml .

CMD python3 ProblemShareBot.py
