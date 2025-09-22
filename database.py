import sqlite3
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class FishingDatabase:
    def __init__(self, db_path='fishing_spots.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица рыболовных мест
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fishing_spots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                city TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                fish_species TEXT,
                description TEXT,
                best_season TEXT,
                access_type TEXT DEFAULT 'бесплатный',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица отчетов о рыбалке
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fishing_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spot_id INTEGER,
                user_id INTEGER,
                report_date DATE,
                fish_caught TEXT,
                weather_conditions TEXT,
                bait_used TEXT,
                rating INTEGER,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (spot_id) REFERENCES fishing_spots (id)
            )
        ''')
        
        # Таблица рейтингов мест
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spot_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spot_id INTEGER,
                user_id INTEGER,
                rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(spot_id, user_id),
                FOREIGN KEY (spot_id) REFERENCES fishing_spots (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Добавляем начальные данные
        self.add_initial_data()
    
    def add_initial_data(self):
        """Добавление начальных данных в базу"""
        initial_spots = [
            # Москва
            {
                'name': 'Химкинское водохранилище',
                'type': 'водохранилище',
                'city': 'москва',
                'latitude': 55.8787,
                'longitude': 37.4382,
                'fish_species': 'щука, окунь, плотва, лещ',
                'description': 'Хорошие места у северного берега, глубина 3-8 метров',
                'best_season': 'круглый год',
                'access_type': 'бесплатный'
            },
            {
                'name': 'Серебряный Бор',
                'type': 'озеро',
                'city': 'москва',
                'latitude': 55.7776,
                'longitude': 37.4267,
                'fish_species': 'карась, карп, линь',
                'description': 'Тихие заводи с растительностью, илистое дно',
                'best_season': 'апрель-октябрь',
                'access_type': 'бесплатный'
            },
            {
                'name': 'Клязьминское водохранилище',
                'type': 'водохранилище',
                'city': 'москва',
                'latitude': 56.0234,
                'longitude': 37.5678,
                'fish_species': 'судак, щука, окунь, лещ',
                'description': 'Чистая вода, много коряжника, перспективные бровки',
                'best_season': 'май-сентябрь',
                'access_type': 'бесплатный'
            },
            
            # Санкт-Петербург
            {
                'name': 'Финский залив',
                'type': 'залив',
                'city': 'санкт-петербург',
                'latitude': 59.9311,
                'longitude': 29.7707,
                'fish_species': 'судак, лещ, плотва, корюшка',
                'description': 'Перспективные места у дамбы, глубина 5-15 метров',
                'best_season': 'круглый год',
                'access_type': 'бесплатный'
            },
            {
                'name': 'Озеро Разлив',
                'type': 'озеро',
                'city': 'санкт-петербург',
                'latitude': 60.1123,
                'longitude': 29.9456,
                'fish_species': 'форель, щука, окунь',
                'description': 'Чистое лесное озеро, каменистое дно',
                'best_season': 'июнь-сентябрь',
                'access_type': 'платный'
            },
            
            # Новосибирск
            {
                'name': 'Обское водохранилище',
                'type': 'водохранилище',
                'city': 'новосибирск',
                'latitude': 54.8567,
                'longitude': 82.9568,
                'fish_species': 'судак, щука, окунь, лещ, язь',
                'description': 'Крупный водоем, много заливов и бухт',
                'best_season': 'май-октябрь',
                'access_type': 'бесплатный'
            },
            
            # Екатеринбург
            {
                'name': 'Волчихинское водохранилище',
                'type': 'водохранилище',
                'city': 'екатеринбург',
                'latitude': 56.8234,
                'longitude': 60.2678,
                'fish_species': 'щука, окунь, плотва, лещ',
                'description': 'Живописный водоем в лесной зоне',
                'best_season': 'май-сентябрь',
                'access_type': 'бесплатный'
            }
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Проверяем, есть ли уже данные
        cursor.execute("SELECT COUNT(*) FROM fishing_spots")
        count = cursor.fetchone()[0]
        
        if count == 0:
            for spot in initial_spots:
                cursor.execute('''
                    INSERT INTO fishing_spots 
                    (name, type, city, latitude, longitude, fish_species, description, best_season, access_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    spot['name'], spot['type'], spot['city'], spot['latitude'],
                    spot['longitude'], spot['fish_species'], spot['description'],
                    spot['best_season'], spot['access_type']
                ))
        
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована с начальными данными")
    
    def get_spots_by_city(self, city):
        """Получить места по городу"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT fs.*, 
                   COALESCE(AVG(sr.rating), 0) as avg_rating,
                   COUNT(sr.id) as rating_count
            FROM fishing_spots fs
            LEFT JOIN spot_ratings sr ON fs.id = sr.spot_id
            WHERE LOWER(fs.city) = LOWER(?)
            GROUP BY fs.id
            ORDER BY avg_rating DESC
        ''', (city,))
        
        spots = []
        for row in cursor.fetchall():
            spot = {
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'city': row[3],
                'latitude': row[4],
                'longitude': row[5],
                'fish_species': row[6],
                'description': row[7],
                'best_season': row[8],
                'access_type': row[9],
                'avg_rating': round(row[10], 1) if row[10] else 0,
                'rating_count': row[11] or 0
            }
            spots.append(spot)
        
        conn.close()
        return spots
    
    def get_spots_by_fish(self, fish_species):
        """Получить места по виду рыбы"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT fs.*, 
                   COALESCE(AVG(sr.rating), 0) as avg_rating
            FROM fishing_spots fs
            LEFT JOIN spot_ratings sr ON fs.id = sr.spot_id
            WHERE LOWER(fs.fish_species) LIKE LOWER(?)
            GROUP BY fs.id
            ORDER BY avg_rating DESC
        ''', (f'%{fish_species}%',))
        
        spots = []
        for row in cursor.fetchall():
            spot = {
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'city': row[3],
                'latitude': row[4],
                'longitude': row[5],
                'fish_species': row[6],
                'description': row[7],
                'best_season': row[8],
                'access_type': row[9],
                'avg_rating': round(row[10], 1) if row[10] else 0
            }
            spots.append(spot)
        
        conn.close()
        return spots
    
    def add_spot_rating(self, spot_id, user_id, rating):
        """Добавить оценку места"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO spot_ratings (spot_id, user_id, rating)
                VALUES (?, ?, ?)
            ''', (spot_id, user_id, rating))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления оценки: {e}")
            return False
        finally:
            conn.close()
    
    def add_fishing_report(self, spot_id, user_id, fish_caught, weather, bait, rating, comment):
        """Добавить отчет о рыбалке"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO fishing_reports 
                (spot_id, user_id, report_date, fish_caught, weather_conditions, bait_used, rating, comment)
                VALUES (?, ?, DATE('now'), ?, ?, ?, ?, ?)
            ''', (spot_id, user_id, fish_caught, weather, bait, rating, comment))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления отчета: {e}")
            return False
        finally:
            conn.close()
    
    def get_recent_reports(self, spot_id=None, limit=5):
        """Получить последние отчеты"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if spot_id:
            cursor.execute('''
                SELECT fr.*, fs.name as spot_name
                FROM fishing_reports fr
                JOIN fishing_spots fs ON fr.spot_id = fs.id
                WHERE fr.spot_id = ?
                ORDER BY fr.created_at DESC
                LIMIT ?
            ''', (spot_id, limit))
        else:
            cursor.execute('''
                SELECT fr.*, fs.name as spot_name
                FROM fishing_reports fr
                JOIN fishing_spots fs ON fr.spot_id = fs.id
                ORDER BY fr.created_at DESC
                LIMIT ?
            ''', (limit,))
        
        reports = []
        for row in cursor.fetchall():
            report = {
                'id': row[0],
                'spot_id': row[1],
                'user_id': row[2],
                'report_date': row[3],
                'fish_caught': row[4],
                'weather_conditions': row[5],
                'bait_used': row[6],
                'rating': row[7],
                'comment': row[8],
                'spot_name': row[10]
            }
            reports.append(report)
        
        conn.close()
        return reports

# Глобальный экземпляр базы данных
fishing_db = FishingDatabase()
