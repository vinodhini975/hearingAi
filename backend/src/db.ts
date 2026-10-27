import sqlite3 from 'sqlite3';
import path from 'path';
import fs from 'fs';

const dbPath = path.resolve(__dirname, '../hearing_screening.db');

// Ensure parent folder exists
const dbDir = path.dirname(dbPath);
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true });
}

// Open database connection
export const db = new sqlite3.Database(dbPath, (err) => {
  if (err) {
    console.error('Error opening SQLite database:', err);
  } else {
    console.log('Successfully connected to SQLite database at:', dbPath);
    initializeDatabase();
  }
});

// Promisified DB helpers
export const dbRun = (sql: string, params: any[] = []): Promise<any> => {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function (err) {
      if (err) reject(err);
      else resolve(this);
    });
  });
};

export const dbGet = (sql: string, params: any[] = []): Promise<any> => {
  return new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });
};

export const dbAll = (sql: string, params: any[] = []): Promise<any[]> => {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });
};

// Initial Schema Setup
async function initializeDatabase() {
  try {
    // Enable foreign keys
    await dbRun('PRAGMA foreign_keys = ON;');

    // Sessions table
    await dbRun(`
      CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        age INTEGER,
        symptoms TEXT,
        headphone_type TEXT,
        device_type TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        data_quality TEXT DEFAULT 'Insufficient data',
        confidence_level TEXT DEFAULT 'Low confidence',
        overall_status TEXT DEFAULT 'Screening incomplete',
        left_status TEXT DEFAULT 'Not tested',
        right_status TEXT DEFAULT 'Not tested',
        hearing_pattern TEXT DEFAULT 'Indeterminate',
        ai_explanation TEXT,
        current_ear TEXT DEFAULT 'LEFT',
        current_stage TEXT DEFAULT 'demographics',
        noise_cancellation_profile TEXT,
        noise_cancellation_level TEXT,
        pathology_classification TEXT,
        fixed_system_volume REAL DEFAULT 0.50,
        audio_device TEXT,
        calibration_profile TEXT
      );
    `);

    // Auto-migration for existing databases
    try {
      await dbRun('ALTER TABLE sessions ADD COLUMN current_ear TEXT DEFAULT "LEFT"');
    } catch (e) {
      // Column already exists
    }

    try {
      await dbRun('ALTER TABLE sessions ADD COLUMN current_stage TEXT DEFAULT "demographics"');
    } catch (e) {
      // Column already exists
    }

    try {
      await dbRun('ALTER TABLE sessions ADD COLUMN noise_cancellation_profile TEXT');
    } catch (e) {
      // Column already exists
    }

    try {
      await dbRun('ALTER TABLE sessions ADD COLUMN noise_cancellation_level TEXT');
    } catch (e) {
      // Column already exists
    }

    try {
      await dbRun('ALTER TABLE sessions ADD COLUMN pathology_classification TEXT');
    } catch (e) {
      // Column already exists
    }

    try {
      await dbRun('ALTER TABLE sessions ADD COLUMN fixed_system_volume REAL DEFAULT 0.50');
    } catch (e) {
      // Column already exists
    }

    try {
      await dbRun('ALTER TABLE sessions ADD COLUMN audio_device TEXT');
    } catch (e) {
      // Column already exists
    }

    try {
      await dbRun('ALTER TABLE sessions ADD COLUMN calibration_profile TEXT');
    } catch (e) {
      // Column already exists
    }

    // Pure-Tone Trials table
    await dbRun(`
      CREATE TABLE IF NOT EXISTS pure_tone_trials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        ear TEXT CHECK(ear IN ('LEFT', 'RIGHT')),
        frequency INTEGER,
        sound_level REAL,
        trial_number INTEGER,
        duration INTEGER,
        response INTEGER CHECK(response IN (0, 1)),
        response_time INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
      );
    `);

    // Speech trials table
    await dbRun(`
      CREATE TABLE IF NOT EXISTS speech_trials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        ear TEXT CHECK(ear IN ('LEFT', 'RIGHT')),
        target_word TEXT,
        user_response TEXT,
        similarity_score REAL,
        is_correct INTEGER CHECK(is_correct IN (0, 1)),
        recording_quality TEXT CHECK(recording_quality IN ('Good', 'Poor', 'Unclear')),
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
      );
    `);

    // Thresholds cache table
    await dbRun(`
      CREATE TABLE IF NOT EXISTS thresholds (
        session_id TEXT,
        ear TEXT CHECK(ear IN ('LEFT', 'RIGHT')),
        frequency INTEGER,
        estimated_level REAL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(session_id, ear, frequency),
        FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
      );
    `);

    console.log('Database tables successfully initialized.');
  } catch (error) {
    console.error('Failed to initialize database tables:', error);
  }
}
