package utils

import (
	"database/sql"
	"time"
)

const SqliteDBPath = "finleap_events.db"

// Initialize SQLite DB and create table if not exists
func InitSqliteDB() (*sql.DB, error) {
	// TODO: remove this after using actual data from ../../cloudtrail-dynamodb instead of SQLite

	db, err := sql.Open("sqlite3", SqliteDBPath)
	if err != nil {
		return nil, err
	}
	createTable := `CREATE TABLE IF NOT EXISTS events (
	       id INTEGER PRIMARY KEY AUTOINCREMENT,
	       username TEXT,
	       resource_id TEXT,
	       timestamp TEXT
       );`
	_, err = db.Exec(createTable)
	if err != nil {
		return nil, err
	}
	return db, nil
}

// Store a create event in SQLite
func StoreCreateEventSqlite(db *sql.DB, event CreateEvent) error {
	// TODO: remove this after using actual data from ../../cloudtrail-dynamodb instead of SQLite

	stmt := `INSERT INTO events (username, resource_id, timestamp) VALUES (?, ?, ?)`
	_, err := db.Exec(stmt, event.Username, event.ResourceId, event.Timestamp.Format(time.RFC3339))
	return err
}

// Get all resources created by each user from SQLite
func GetUserResourcesSqlite(db *sql.DB) (map[string][]string, error) {
	// TODO: use actual data from ../../cloudtrail-dynamodb instead of SQLite

	result := make(map[string][]string)
	rows, err := db.Query(`SELECT username, resource_id FROM events`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	for rows.Next() {
		var username, resourceId string
		if err := rows.Scan(&username, &resourceId); err != nil {
			continue
		}
		result[username] = append(result[username], resourceId)
	}
	return result, nil
}
