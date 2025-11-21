package main

import (
	"cost-calculator/config"
	"cost-calculator/database"
	"cost-calculator/handlers"
	"log"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

func main() {
	cfg := config.Load()

	database.Connect(cfg)

	r := gin.Default()

	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"http://localhost:5173", "http://127.0.0.1:5173", "http://3.108.187.54:5173"},
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Authorization"},
		AllowCredentials: true,
	}))

	api := r.Group("/api/v1")
	{
		api.GET("/costs/principals", handlers.GetPrincipalCosts)
		api.GET("/costs/principals/:id", handlers.GetPrincipalCostByID)
		api.GET("/principals/resources", handlers.GetPrincipalResourceMapping)
		api.GET("/instances", handlers.GetInstanceCosts)
	}

	log.Printf("Server starting on port %s", cfg.ServerPort)
	r.Run(":" + cfg.ServerPort)
}
