from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
from sqlalchemy.orm import Session, aliased
import json

from db import init_db, Tournament, Team, Match, User, Participation, Bet
from auth import get_current_user, verify_telegram_data, parse_user_data, create_jwt_token, is_user_admin, is_user_authorized
from config import logger

router = APIRouter()

engine = init_db()

def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_class=HTMLResponse)
async def index():
    logger.debug("Serving index page")
    with open("templates/index.html") as f:
        return f.read()

@router.post("/init")
async def init_mini_app(request: Request):
    try:
        logger.debug("Processing mini app initialization request")
        data = await request.json()
        init_data = data.get('initData')
        
        if not init_data:
            logger.warning("No initData provided in request")
            raise HTTPException(status_code=400, detail="No initData provided")
        
        is_verified_telegram_user = verify_telegram_data(init_data)
        if not is_verified_telegram_user:
            logger.warning("Invalid Telegram data in init request")
            raise HTTPException(status_code=401, detail="Invalid Telegram data")
        
        user_data = parse_user_data(init_data)
        if not user_data:
            logger.warning("Missing user in Telegram initData")
            raise HTTPException(status_code=401, detail="Invalid user data")

        user_id = int(user_data.get("id"))        
        if not user_id:
            logger.warning("Missing user ID in Telegram data")
            raise HTTPException(status_code=401, detail="Invalid user data")
        
        # Check if user is authorized
        is_authorized = is_user_authorized(user_id)
        is_admin = is_user_admin(user_id)
        # Create JWT token for authorized users
        token = None
        if is_authorized:
            token = create_jwt_token(user_data)
            logger.debug(f"Created JWT token for authorized user {user_id}")
        
        logger.debug(f"Successfully initialized mini app for user {user_id}")
        
        return JSONResponse({
            "status": "success",
            "authenticated": is_authorized,
            "token": token,
            "is_admin": is_admin,
            "user_data": user_data
        })
    except Exception as e:
        logger.error(f"Error processing init request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add_tournament")
async def add_tournament(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        tournament_name = data.get('name_ru')
        
        if not tournament_name:
            raise HTTPException(status_code=400, detail="Tournament name is required")
        
        # Create new tournament
        tournament = Tournament(name_ru=tournament_name)
        db.add(tournament)
        db.commit()
        db.refresh(tournament)
        
        return JSONResponse({
            "success": True,
            "tournament_id": tournament.id
        })
    except Exception as e:
        logger.error(f"Error adding tournament: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add_match")
async def add_match(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        tournament_id = data.get('tournament_id')
        team_1_id = data.get('team_1_id')
        team_2_id = data.get('team_2_id')
        match_date = data.get('date')
        
        if not all([tournament_id, team_1_id, team_2_id, match_date]):
            raise HTTPException(status_code=400, detail="All fields are required")
        
        # Get tournament by ID
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not tournament:
            raise HTTPException(status_code=404, detail="Tournament not found")
        
        # Get teams by ID
        team1 = db.query(Team).filter(Team.id == team_1_id).first()
        if not team1:
            raise HTTPException(status_code=404, detail="Team 1 not found")
            
        team2 = db.query(Team).filter(Team.id == team_2_id).first()
        if not team2:
            raise HTTPException(status_code=404, detail="Team 2 not found")
        
        # Create match
        match = Match(
            tournament_id=tournament.id,
            team_1_id=team1.id,
            team_2_id=team2.id,
            start_time_utc=datetime.fromisoformat(match_date.replace('Z', '+00:00'))
        )
        db.add(match)
        db.commit()
        db.refresh(match)
        
        return JSONResponse({
            "success": True,
            "match_id": match.id
        })
    except Exception as e:
        logger.error(f"Error adding match: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tournaments")
async def get_tournaments(db: Session = Depends(get_db)):
    try:
        tournaments = db.query(Tournament).all()
        return JSONResponse({
            "success": True,
            "tournaments": [{"id": t.id, "name_ru": t.name_ru} for t in tournaments]
        })
    except Exception as e:
        logger.error(f"Error getting tournaments: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/teams")
async def get_teams(db: Session = Depends(get_db)):
    try:
        teams = db.query(Team).all()
        return JSONResponse({
            "success": True,
            "teams": [{"id": t.id, "name_ru": t.name_ru} for t in teams]
        })
    except Exception as e:
        logger.error(f"Error getting teams: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add_team")
async def add_team(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        team_name = data.get('name_ru')
        
        if not team_name:
            raise HTTPException(status_code=400, detail="Team name is required")
        
        # Create new team
        team = Team(name_ru=team_name)
        db.add(team)
        db.commit()
        db.refresh(team)
        
        return JSONResponse({
            "success": True,
            "team_id": team.id
        })
    except Exception as e:
        logger.error(f"Error adding team: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available-tournaments")
async def get_available_tournaments(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    try:
        # Get tournaments where user is not already participating
        db_user = db.query(User).filter(User.tg_id == user['id']).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        existing_participations = db.query(Participation.tournament_id).filter(
            Participation.user_id == db_user.id
        ).all()
        existing_tournament_ids = [p[0] for p in existing_participations]

        available_tournaments = db.query(Tournament).filter(
            ~Tournament.id.in_(existing_tournament_ids)
        ).all()

        return JSONResponse({
            "success": True,
            "tournaments": [{"id": t.id, "name_ru": t.name_ru} for t in available_tournaments]
        })
    except Exception as e:
        logger.error(f"Error getting available tournaments: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/participate")
async def participate_in_tournament(request: Request, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    try:
        data = await request.json()
        tournament_id = data.get('tournament_id')
        
        if not tournament_id:
            raise HTTPException(status_code=400, detail="Tournament ID is required")
        
        # Get or create user
        db_user = db.query(User).filter(User.tg_id == user['id']).first()
        if not db_user:
            db_user = User(
                tg_id=user['id'],
                name=user.get('first_name', '') + ' ' + user.get('last_name', '')
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
        
        # Check if already participating
        existing = db.query(Participation).filter(
            Participation.user_id == db_user.id,
            Participation.tournament_id == tournament_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Already participating in this tournament")
        
        # Create participation
        participation = Participation(
            user_id=db_user.id,
            tournament_id=tournament_id,
            approved=False
        )
        db.add(participation)
        db.commit()
        
        return JSONResponse({
            "success": True,
            "message": "Participation request submitted"
        })
    except Exception as e:
        logger.error(f"Error participating in tournament: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pending-participations")
async def get_pending_participations(db: Session = Depends(get_db)):
    try:
        # Get pending participations with user and tournament info
        participations = db.query(
            Participation,
            User.name.label('user_name'),
            Tournament.name_ru.label('tournament_name')
        ).join(
            User, Participation.user_id == User.id
        ).join(
            Tournament, Participation.tournament_id == Tournament.id
        ).filter(
            Participation.approved == False
        ).all()
        
        return JSONResponse({
            "success": True,
            "participations": [
                {
                    "id": p.Participation.id,
                    "user_name": p.user_name,
                    "tournament_name": p.tournament_name
                }
                for p in participations
            ]
        })
    except Exception as e:
        logger.error(f"Error getting pending participations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approve-participation")
async def approve_participation(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        participation_id = data.get('participation_id')
        
        if not participation_id:
            raise HTTPException(status_code=400, detail="Participation ID is required")
        
        # Update participation
        participation = db.query(Participation).filter(Participation.id == participation_id).first()
        if not participation:
            raise HTTPException(status_code=404, detail="Participation not found")
        
        participation.approved = True
        db.commit()
        
        return JSONResponse({
            "success": True,
            "message": "Participation approved"
        })
    except Exception as e:
        logger.error(f"Error approving participation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user-matches")
async def get_user_matches(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    try:
        Team1 = aliased(Team)
        Team2 = aliased(Team)

        matches = db.query(
            Match,
            Tournament.name_ru.label('tournament_name'),
            Team1.name_ru.label('team_1_name'),
            Team2.name_ru.label('team_2_name'),
            Bet.score_1.label('bet_score_1'),
            Bet.score_2.label('bet_score_2'),
            Bet.points
        ).join(
            Tournament, Match.tournament_id == Tournament.id
        ).join(
            Participation, 
            (Participation.tournament_id == Match.tournament_id) & 
            (Participation.approved == True)
        ).join(
            User,
            (User.id == Participation.user_id) &
            (User.tg_id == user["id"])
        ).join(
            Team1, Match.team_1_id == Team1.id
        ).join(
            Team2, Match.team_2_id == Team2.id
        ).outerjoin(
            Bet, (Bet.match_id == Match.id) & (Bet.user_id == user['id'])
        ).all()
        logger.debug(f"matches {matches}")
        
        # Формируем ответ
        matches_data = []
        for match, tournament_name, team1_name, team2_name, bet_score_1, bet_score_2, points in matches:
            match_data = {
                'id': match.id,
                'tournament_name': tournament_name,
                'team_1_name': team1_name,
                'team_2_name': team2_name,
                'date': match.start_time_utc.isoformat(),
                'score_1': match.score_1,
                'score_2': match.score_2,
                'bet': {
                    'score_1': bet_score_1,
                    'score_2': bet_score_2,
                    'points': points
                } if bet_score_1 is not None else None
            }
            matches_data.append(match_data)
        
        return JSONResponse({
            "success": True,
            "matches": matches_data
        })
    except Exception as e:
        logger.error(f"Error getting user matches and bets: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending-matches")
async def get_pending_matches(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    try:
        Team1 = aliased(Team)
        Team2 = aliased(Team)

        matches = db.query(
            Match,
            Tournament.name_ru.label('tournament_name'),
            Team1.name_ru.label('team_1_name'),
            Team2.name_ru.label('team_2_name')
        ).join(
            Tournament, Match.tournament_id == Tournament.id
        ).join(
            Team1, Match.team_1_id == Team1.id
        ).join(
            Team2, Match.team_2_id == Team2.id
        ).all()
        logger.debug(f"matches {matches}")
        
        # Формируем ответ
        matches_data = []
        for match, tournament_name, team1_name, team2_name in matches:
            match_data = {
                'id': match.id,
                'tournament_name': tournament_name,
                'team_1_name': team1_name,
                'team_2_name': team2_name,
                'date': match.start_time_utc.isoformat(),
                'score_1': match.score_1,
                'score_2': match.score_2,
            }
            matches_data.append(match_data)
        
        return JSONResponse({
            "success": True,
            "matches": matches_data
        })
    except Exception as e:
        logger.error(f"Error getting user matches and bets: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/place-bet")
async def place_bet(request: Request, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    try:
        data = await request.json()
        logger.debug(f"data {data}")
        match_id = data.get('match_id')
        score_1 = int(data.get('score_1'))
        score_2 = int(data.get('score_2'))
        
        if not all([match_id, score_1 is not None, score_2 is not None]):
            logger.debug(f"Missing required fields")
            return JSONResponse({
                "success": False,
                "error": "Missing required fields"
            }, status_code=400)
        
        # Проверяем, что матч еще не начался
        match = db.query(Match).filter(Match.id == match_id).first()
        logger.debug(f"match {match}")
        if not match:
            return JSONResponse({
                "success": False,
                "error": "Match not found"
            }, status_code=404)
        
        if match.start_time_utc <= datetime.now():
            logger.debug(f"Cannot place bet on started match")
            return JSONResponse({
                "success": False,
                "error": "Cannot place bet on started match"
            }, status_code=400)
        
        # Проверяем, что пользователь участвует в турнире
        participation = db.query(
            Participation
        ).join(
            User, 
            (Participation.user_id == User.id) & 
            (User.tg_id == user["id"])
        ).filter(
            Participation.tournament_id == match.tournament_id,
            Participation.approved == True
        ).first()
        
        if not participation:
            return JSONResponse({
                "success": False,
                "error": "User is not participating in this tournament"
            }, status_code=403)
        
        # Создаем или обновляем ставку
        bet = db.query(Bet).filter(
            Bet.user_id == user['id'],
            Bet.match_id == match_id
        ).first()
        
        if bet:
            bet.score_1 = score_1
            bet.score_2 = score_2
        else:
            bet = Bet(
                user_id=user['id'],
                match_id=match_id,
                score_1=score_1,
                score_2=score_2
            )
            db.add(bet)
        
        db.commit()
        return JSONResponse({
            "success": True
        })
    except Exception as e:
        logger.error(f"Error placing bet: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 