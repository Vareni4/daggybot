from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, Double
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Tournament(Base):
    __tablename__ = 'tournaments'
    
    id = Column(Integer, primary_key=True)
    name_ru = Column(String, nullable=False)
    
    matches = relationship("Match", back_populates="tournament")
    participations = relationship("Participation", back_populates="tournament")

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True, nullable=False)
    name = Column(String, nullable=False)
    
    bets = relationship("Bet", back_populates="user")
    participations = relationship("Participation", back_populates="user")

class Team(Base):
    __tablename__ = 'teams'
    
    id = Column(Integer, primary_key=True)
    name_ru = Column(String, nullable=False)
    
    matches_as_team1 = relationship("Match", foreign_keys="Match.team_1_id", back_populates="team1")
    matches_as_team2 = relationship("Match", foreign_keys="Match.team_2_id", back_populates="team2")

class Match(Base):
    __tablename__ = 'matches'
    
    id = Column(Integer, primary_key=True)
    tournament_id = Column(Integer, ForeignKey('tournaments.id'), nullable=False)
    team_1_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    team_2_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    start_time_utc = Column(DateTime, nullable=False)
    score_1 = Column(Integer, nullable=True)
    score_2 = Column(Integer, nullable=True)
    is_finished = Column(Boolean, default=False)
    
    tournament = relationship("Tournament", back_populates="matches")
    team1 = relationship("Team", foreign_keys=[team_1_id], back_populates="matches_as_team1")
    team2 = relationship("Team", foreign_keys=[team_2_id], back_populates="matches_as_team2")
    bets = relationship("Bet", back_populates="match")

class Bet(Base):
    __tablename__ = 'bets'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    match_id = Column(Integer, ForeignKey('matches.id'), nullable=False)
    score_1 = Column(Integer, nullable=False)
    score_2 = Column(Integer, nullable=False)
    points = Column(Double, nullable=True)
    
    user = relationship("User", back_populates="bets")
    match = relationship("Match", back_populates="bets")

class Participation(Base):
    __tablename__ = 'participations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    tournament_id = Column(Integer, ForeignKey('tournaments.id'), nullable=False)
    approved = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="participations")
    tournament = relationship("Tournament", back_populates="participations")

def init_db():
    engine = create_engine('sqlite:///daggybot.db')
    Base.metadata.create_all(engine)
    return engine

if __name__ == "__main__":
    init_db()
