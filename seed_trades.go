package main

import (
	"context"
	"fmt"
	"log"
	"math/rand"
	"os"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
)

// Realistic trader stats: ~55% win rate, wins are typically 1.5x to 3x risk.
// We will generate trades for the last 60 days.
func main() {
	dbURL := "user=etradie password=etradie123abcChuks host=localhost port=5433 dbname=etradie sslmode=disable"
	if envURL := os.Getenv("DATABASE_URL"); envURL != "" {
		dbURL = envURL
	}

	ctx := context.Background()
	pool, err := pgxpool.New(ctx, dbURL)
	if err != nil {
		log.Fatalf("Failed to connect to DB: %v", err)
	}
	defer pool.Close()

	// Find the user 'Flame Great' in the system
	var userID string
	err = pool.QueryRow(ctx, "SELECT id FROM auth_users WHERE username = $1", "Flame Great").Scan(&userID)
	if err != nil {
		log.Println("Could not find user 'flamegreat' in auth_users. Searching for any available user...")
		err = pool.QueryRow(ctx, "SELECT id FROM auth_users LIMIT 1").Scan(&userID)
		if err != nil {
			log.Println("Could not find any user in auth_users. Using fallback user_id 'system'.")
			userID = "system"
		}
	}

	fmt.Printf("Seeding trades for user: %s\n", userID)

	now := time.Now()
	// Seed last 60 days
	startDate := now.AddDate(0, 0, -60)

	symbols := []string{"EURUSD", "GBPUSD", "XAUUSD", "US30", "NAS100"}
	styles := []string{"DAY_TRADING", "SCALPING", "SWING"}
	directions := []string{"LONG", "SHORT"}

	// Delete existing seeded trades to prevent clutter
	_, err = pool.Exec(ctx, "DELETE FROM management_trades WHERE broker_order_id LIKE 'SEED_%'")
	if err != nil {
		log.Fatalf("Failed to clean old seeds: %v", err)
	}

	seededCount := 0

	for d := startDate; d.Before(now); d = d.AddDate(0, 0, 1) {
		// Skip weekends (mostly)
		if d.Weekday() == time.Saturday || d.Weekday() == time.Sunday {
			if rand.Float32() > 0.1 { // 10% chance of trading crypto on weekend
				continue
			}
		}

		// 1 to 4 trades a day
		tradesToday := rand.Intn(4) + 1
		for i := 0; i < tradesToday; i++ {
			symbol := symbols[rand.Intn(len(symbols))]
			direction := directions[rand.Intn(len(directions))]
			style := styles[rand.Intn(len(styles))]

			// Realistic base prices
			var basePrice, volatility float64
			switch symbol {
			case "EURUSD":
				basePrice = 1.1785 + (rand.Float64()*0.005 - 0.0025)
				volatility = 0.0020
			case "GBPUSD":
				basePrice = 1.3632 + (rand.Float64()*0.005 - 0.0025)
				volatility = 0.0025
			case "XAUUSD":
				basePrice = 4700.0 + (rand.Float64()*50.0 - 25.0)
				volatility = 10.0
			case "US30":
				basePrice = 49600.0 + (rand.Float64()*500.0 - 250.0)
				volatility = 80.0
			case "NAS100":
				basePrice = 29200.0 + (rand.Float64()*300.0 - 150.0)
				volatility = 50.0
			}

			// Determine Outcome (61% win rate)
			isWin := rand.Float32() <= 0.61
			
			riskAmount := float64(100 + rand.Intn(400)) // Risking $100-$500 per trade
			var grossPnL float64
			var rMultiple float64
			
			if isWin {
				// Win: 1.5R to 3.5R
				rMultiple = 1.5 + (rand.Float64() * 2.0)
				grossPnL = riskAmount * rMultiple
			} else {
				// Loss: exactly -1R or slightly less if slippage/early close
				if rand.Float32() > 0.2 {
					rMultiple = -1.0
					grossPnL = -riskAmount
				} else {
					// Early close loss
					rMultiple = -0.5 - (rand.Float64() * 0.4)
					grossPnL = riskAmount * rMultiple
				}
			}

			// Calculate Entry, Exit, SL
			entryPrice := basePrice
			var exitPrice, stopLoss float64
			slDistance := volatility * (0.8 + rand.Float64()*0.4) // Randomize SL size slightly

			if direction == "LONG" {
				stopLoss = entryPrice - slDistance
				exitPrice = entryPrice + (slDistance * rMultiple)
			} else {
				stopLoss = entryPrice + slDistance
				exitPrice = entryPrice - (slDistance * rMultiple)
			}

			// Randomize trade duration (15 mins to 4 hours)
			durationMins := 15 + rand.Intn(240)
			
			// Open time is somewhere in the day
			hour := 8 + rand.Intn(8) // 8 AM to 4 PM
			openedAt := time.Date(d.Year(), d.Month(), d.Day(), hour, rand.Intn(60), 0, 0, d.Location())
			closedAt := openedAt.Add(time.Duration(durationMins) * time.Minute)

			// Ensure we don't insert future trades
			if closedAt.After(now) {
				continue
			}

			tradeID := uuid.New().String()
			brokerOrderID := "SEED_" + uuid.New().String()[:8]

			outcomeStr := "LOSS"
			if grossPnL > 0 {
				outcomeStr = "WIN"
			} else if grossPnL == 0 {
				outcomeStr = "BREAKEVEN"
			}

			_, err = pool.Exec(ctx, `
				INSERT INTO management_trades (
					user_id, trade_id, symbol, direction, entry_price, exit_price, stop_loss, initial_sl,
					tp1_price, tp2_price, tp3_price, total_lot_size,
					risk_amount, risk_percent, confluence_score, grade,
					setup_type, trading_style, session, execution_mode,
					slippage, status, analysis_id, broker_order_id, opened_at, closed_at,
					gross_pnl, r_multiple, outcome, duration_minutes
				) VALUES (
					$1, $2, $3, $4, $5, $6, $7, $8,
					0, 0, 0, 1.0,
					$9, 1.0, 8.5, 'A',
					'A+', $10, 'NEW_YORK', 'MARKET',
					0, 'CLOSED', 'seed_analysis', $11, $12, $13,
					$14, $15, $16, $17
				)`,
				userID, tradeID, symbol, direction,
				entryPrice, exitPrice, stopLoss, stopLoss,
				riskAmount, style, brokerOrderID, openedAt, closedAt,
				grossPnL, rMultiple, outcomeStr, durationMins,
			)

			if err != nil {
				log.Printf("Error inserting trade: %v", err)
			} else {
				seededCount++
			}
		}
	}

	fmt.Printf("Successfully generated %d realistic past trades for the PnL Calendar.\n", seededCount)
}
