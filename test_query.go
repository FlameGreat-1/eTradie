package main

import (
	"context"
	"fmt"
	"log"

	"github.com/jackc/pgx/v5/pgxpool"
)

func main() {
	dbURL := "user=etradie password=etradie123abcChuks host=localhost port=5433 dbname=etradie sslmode=disable"
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, dbURL)
	if err != nil {
		log.Fatalf("Failed to connect: %v", err)
	}
	defer pool.Close()

	var userID string
	err = pool.QueryRow(ctx, "SELECT id FROM auth_users WHERE username = $1", "flamegreat").Scan(&userID)
	if err != nil {
		log.Fatalf("Failed to find user: %v", err)
	}

	tz := "UTC"
	year := 2026
	month := 5

	query := `
		SELECT
			TO_CHAR(closed_at AT TIME ZONE $4, 'YYYY-MM-DD') AS day,
			SUM(gross_pnl) AS pnl
		FROM management_trades
		WHERE status = 'CLOSED'
		  AND user_id = $1
		  AND EXTRACT(YEAR FROM closed_at AT TIME ZONE $4) = $2
		  AND EXTRACT(MONTH FROM closed_at AT TIME ZONE $4) = $3
		GROUP BY day
		ORDER BY day`

	rows, err := pool.Query(ctx, query, userID, year, month, tz)
	if err != nil {
		log.Fatalf("Query failed: %v", err)
	}
	defer rows.Close()

	count := 0
	for rows.Next() {
		var day string
		var pnl float64
		err := rows.Scan(&day, &pnl)
		if err != nil {
			log.Fatalf("Scan failed: %v", err)
		}
		fmt.Printf("Day: %s, PnL: %f\n", day, pnl)
		count++
	}
	fmt.Printf("Total days: %d\n", count)
}
