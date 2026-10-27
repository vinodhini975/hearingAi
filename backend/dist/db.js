"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.dbAll = exports.dbGet = exports.dbRun = exports.db = void 0;
const sqlite3_1 = __importDefault(require("sqlite3"));
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
const dbPath = path_1.default.resolve(__dirname, '../hearing_screening.db');
// Ensure parent folder exists
const dbDir = path_1.default.dirname(dbPath);
if (!fs_1.default.existsSync(dbDir)) {
    fs_1.default.mkdirSync(dbDir, { recursive: true });
}
// Open database connection
exports.db = new sqlite3_1.default.Database(dbPath, (err) => {
    if (err) {
        console.error('Error opening SQLite database:', err);
    }
    else {
        console.log('Successfully connected to SQLite database at:', dbPath);
        initializeDatabase();
    }
});
// Promisified DB helpers
const dbRun = (sql, params = []) => {
    return new Promise((resolve, reject) => {
        exports.db.run(sql, params, function (err) {
            if (err)
                reject(err);
            else
                resolve(this);
        });
    });
};
exports.dbRun = dbRun;
const dbGet = (sql, params = []) => {
    return new Promise((resolve, reject) => {
        exports.db.get(sql, params, (err, row) => {
            if (err)
                reject(err);
            else
                resolve(row);
        });
    });
};
exports.dbGet = dbGet;
const dbAll = (sql, params = []) => {
    return new Promise((resolve, reject) => {
        exports.db.all(sql, params, (err, rows) => {
            if (err)
                reject(err);
            else
                resolve(rows);
        });
    });
};
exports.dbAll = dbAll;
// Initial Schema Setup
async function initializeDatabase() {
    try {
        // Enable foreign keys
        await (0, exports.dbRun)('PRAGMA foreign_keys = ON;');
        // Sessions table
        await (0, exports.dbRun)(`
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
            await (0, exports.dbRun)('ALTER TABLE sessions ADD COLUMN current_ear TEXT DEFAULT "LEFT"');
        }
        catch (e) {
            // Column already exists
        }
        try {
            await (0, exports.dbRun)('ALTER TABLE sessions ADD COLUMN current_stage TEXT DEFAULT "demographics"');
        }
        catch (e) {
            // Column already exists
        }
        try {
            await (0, exports.dbRun)('ALTER TABLE sessions ADD COLUMN noise_cancellation_profile TEXT');
        }
        catch (e) {
            // Column already exists
        }
        try {
            await (0, exports.dbRun)('ALTER TABLE sessions ADD COLUMN noise_cancellation_level TEXT');
        }
        catch (e) {
            // Column already exists
        }
        try {
            await (0, exports.dbRun)('ALTER TABLE sessions ADD COLUMN pathology_classification TEXT');
        }
        catch (e) {
            // Column already exists
        }
        try {
            await (0, exports.dbRun)('ALTER TABLE sessions ADD COLUMN fixed_system_volume REAL DEFAULT 0.50');
        }
        catch (e) {
            // Column already exists
        }
        try {
            await (0, exports.dbRun)('ALTER TABLE sessions ADD COLUMN audio_device TEXT');
        }
        catch (e) {
            // Column already exists
        }
        try {
            await (0, exports.dbRun)('ALTER TABLE sessions ADD COLUMN calibration_profile TEXT');
        }
        catch (e) {
            // Column already exists
        }
        // Pure-Tone Trials table
        await (0, exports.dbRun)(`
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
        await (0, exports.dbRun)(`
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
        await (0, exports.dbRun)(`
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
    }
    catch (error) {
        console.error('Failed to initialize database tables:', error);
    }
}
