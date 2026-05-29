# Implementation Plan: IPL Live Score Integration

## Overview

This implementation plan breaks down the IPL live score integration enhancement into discrete coding tasks. The approach follows an incremental strategy: establish core infrastructure first, then add live score integration, enhance the prediction system, add social features, implement data visualization, and finally integrate everything together.

The implementation uses the existing tech stack:
- **Backend**: Python with FastAPI
- **Frontend**: Vanilla JavaScript
- **Database**: SQLite for development, PostgreSQL for production
- **Real-time**: WebSockets for live updates
- **Testing**: Hypothesis (Python) and fast-check (JavaScript) for property-based testing

## Tasks

- [x] 1. Set up database schema and data models
  - Create database migration scripts for all tables (users, predictions, match_history, player_stats, team_standings, achievements)
  - Implement Pydantic models for all data structures (LiveMatch, BallEvent, Prediction, PlayerStats, TeamStanding, ChatMessage, Reaction)
  - Create database connection manager supporting both SQLite and PostgreSQL
  - Implement base repository pattern for database operations
  - _Requirements: 8.1, 8.2, 8.4_

- [x] 1.1 Write property test for database round-trip
  - **Property 5: Data persistence round-trip**
  - **Validates: Requirements 2.2, 8.1, 8.2, 8.3**

- [x] 1.2 Write property test for transaction atomicity
  - **Property 24: Transaction atomicity**
  - **Validates: Requirements 8.5**

- [x] 2. Implement caching layer
  - Create CacheService interface with get/set/delete/exists methods
  - Implement in-memory cache with TTL support for development
  - Implement Redis cache adapter for production
  - Add cache key generation utilities
  - Configure TTL values (10s for live data, 60s for schedules, 300s for historical)
  - _Requirements: 7.1, 7.2_

- [x] 2.1 Write property test for cache-first retrieval
  - **Property 20: Cache-first data retrieval**
  - **Validates: Requirements 7.1**

- [x] 3. Implement rate limiter
  - Create RateLimiter class using token bucket algorithm
  - Support configurable rate limits per endpoint (6 requests/minute for Cricbuzz)
  - Implement request queuing when rate limit is reached
  - Add get_wait_time method to inform callers of next available slot
  - _Requirements: 7.3, 7.5_

- [x] 3.1 Write property test for rate limiter enforcement
  - **Property 21: Rate limiter enforcement**
  - **Validates: Requirements 7.3**

- [x] 3.2 Write property test for request queuing
  - **Property 23: Request queuing when rate limited**
  - **Validates: Requirements 7.5**

- [x] 4. Implement Cricbuzz API client
  - Create CricbuzzAPIClient class with methods for fetching live matches, match details, and commentary
  - Implement HTTP request handling with 2-second timeout
  - Add retry logic with exponential backoff (max 3 retries)
  - Parse Cricbuzz API responses into internal data models
  - Handle API errors gracefully with appropriate error types
  - _Requirements: 1.1, 1.4, 9.1_

- [x] 4.1 Write unit tests for API error handling
  - Test timeout scenarios, invalid responses, and network failures
  - _Requirements: 1.4, 9.1_

- [x] 5. Checkpoint - Ensure infrastructure tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Live Match Service
  - Create LiveMatchService class with methods for get_live_matches, get_match_details, get_ball_by_ball
  - Implement periodic polling using asyncio tasks (every 10-15 seconds)
  - Integrate with CacheService to check cache before API calls
  - Integrate with RateLimiter to control API request frequency
  - Implement start_live_updates and stop_live_updates for managing polling tasks
  - Broadcast updates via WebSocket when new data arrives
  - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.7_

- [x] 6.1 Write property test for live match display completeness
  - **Property 1: Live match display completeness**
  - **Validates: Requirements 1.5**

- [x] 6.2 Write property test for match completion persistence
  - **Property 3: Match completion persistence**
  - **Validates: Requirements 1.7**

- [x] 6.3 Write unit tests for polling behavior
  - Test periodic updates, start/stop functionality, concurrent match handling
  - _Requirements: 1.2, 1.3_

- [x] 7. Implement match schedule and history endpoints
  - Create REST API endpoint GET /api/matches/schedule for upcoming matches
  - Create REST API endpoint GET /api/matches/history for completed matches
  - Create REST API endpoint GET /api/matches/{match_id}/highlights for match timeline
  - Implement service methods to fetch from database and format responses
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 7.1 Write property test for schedule display completeness
  - **Property 4: Schedule display completeness**
  - **Validates: Requirements 2.1**

- [x] 7.2 Write property test for match highlights display
  - **Property 6: Match highlights display**
  - **Validates: Requirements 2.3**

- [x] 7.3 Write property test for historical data completeness
  - **Property 7: Historical data completeness**
  - **Validates: Requirements 2.4**

- [x] 7.4 Write property test for chronological ordering
  - **Property 8: Chronological match ordering**
  - **Validates: Requirements 2.5**

- [x] 8. Implement enhanced Prediction Service
  - Create PredictionService class with create_prediction, evaluate_prediction, get_user_predictions methods
  - Implement separate tracking for live vs simulated match predictions
  - Implement streak bonus calculation (2x for 3+ correct, 3x for 5+ correct)
  - Create get_leaderboard method with filtering by match type
  - Implement calculate_streak_bonus method
  - Add prediction locking logic (lock after ball is bowled)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 8.1 Write property test for prediction metadata completeness
  - **Property 9: Prediction metadata completeness**
  - **Validates: Requirements 3.1, 3.2**

- [x] 8.2 Write property test for leaderboard filtering
  - **Property 10: Leaderboard filtering correctness**
  - **Validates: Requirements 3.3, 3.5**

- [x] 8.3 Write property test for streak bonus calculation
  - **Property 11: Streak bonus calculation**
  - **Validates: Requirements 3.4**

- [x] 8.4 Write property test for prediction history with accuracy
  - **Property 12: Prediction history with accuracy**
  - **Validates: Requirements 3.6**

- [x] 8.5 Write property test for XP update propagation
  - **Property 13: XP update propagation**
  - **Validates: Requirements 3.7**

- [x] 9. Checkpoint - Ensure prediction system tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement Statistics Service
  - Create StatisticsService class with update_player_stats, get_player_stats, get_team_standings methods
  - Implement SQL queries for aggregating player statistics (runs, wickets, strike rate, economy)
  - Implement update_team_standings method to calculate points and net run rate
  - Add caching for aggregated statistics (5-minute TTL)
  - Create REST API endpoints for player stats and team standings
  - _Requirements: 4.1, 4.2, 4.4_

- [x] 10.1 Write property test for statistics display completeness
  - **Property 14: Statistics display completeness**
  - **Validates: Requirements 4.2, 4.4**

- [x] 10.2 Write unit tests for stat calculations
  - Test strike rate, economy rate, net run rate calculations with specific examples
  - _Requirements: 4.1, 4.2_

- [x] 11. Implement WebSocket server and Chat Service
  - Create WebSocketManager class with connect, disconnect, send_personal_message, broadcast_to_match methods
  - Implement connection pooling per match
  - Add heartbeat/ping mechanism (every 30 seconds)
  - Create ChatService class with join_room, leave_room, broadcast_message, broadcast_reaction methods
  - Implement message rate limiting (5 messages per user per minute)
  - Store recent messages in cache (last 100 per room)
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 9.2_

- [x] 11.1 Write property test for chat room connection
  - **Property 15: Chat room connection**
  - **Validates: Requirements 5.1**

- [x] 11.2 Write property test for room broadcast delivery
  - **Property 16: Room broadcast delivery**
  - **Validates: Requirements 5.3, 5.5**

- [x] 11.3 Write property test for emoji reaction support
  - **Property 17: Emoji reaction support**
  - **Validates: Requirements 5.4**

- [x] 11.4 Write property test for WebSocket reconnection
  - **Property 25: WebSocket reconnection with backoff**
  - **Validates: Requirements 9.2**

- [x] 12. Implement achievement badge system
  - Create achievement definitions (10 correct predictions, 100 total predictions, 5-streak, etc.)
  - Implement badge awarding logic triggered by prediction evaluations
  - Create REST API endpoint GET /api/users/{user_id}/achievements
  - Store achievements in database
  - _Requirements: 5.6_

- [x] 12.1 Write property test for achievement badge awarding
  - **Property 18: Achievement badge awarding**
  - **Validates: Requirements 5.6**

- [x] 13. Implement user profile endpoint
  - Create REST API endpoint GET /api/users/{user_id}/profile
  - Aggregate user statistics, badges, and prediction history
  - Format response with all required profile information
  - _Requirements: 5.7_

- [x] 13.1 Write property test for profile display completeness
  - **Property 19: Profile display completeness**
  - **Validates: Requirements 5.7**

- [x] 14. Implement poll system
  - Create Poll data model and database table
  - Create REST API endpoints for creating and responding to polls
  - Implement poll broadcast via WebSocket to match rooms
  - Store poll responses and aggregate results
- _Requirements: 5.5_

- [x] 15. Checkpoint - Ensure social features tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 16. Implement error handling and resilience
  - Add error handling middleware to FastAPI application
  - Implement fallback to cached data when API fails
  - Implement operation queuing during database outages
  - Create user-friendly error message formatter
  - Implement comprehensive logging with context (timestamp, user, action, result)
  - Add error recovery for all service methods
  - _Requirements: 9.1, 9.3, 9.4, 9.5, 9.6, 7.6_

- [x] 16.1 Write property test for fallback to cache on failure
  - **Property 22: Fallback to cache on failure**
  - **Validates: Requirements 7.4, 9.5**

- [x] 16.2 Write property test for operation queuing during outage
  - **Property 26: Operation queuing during database outage**
  - **Validates: Requirements 9.3**

- [x] 16.3 Write property test for user-friendly error messages
  - **Property 27: User-friendly error messages**
  - **Validates: Requirements 9.4**

- [x] 16.4 Write property test for comprehensive logging
  - **Property 28: Comprehensive event logging**
  - **Validates: Requirements 7.6, 9.6**

- [x] 16.5 Write unit tests for specific error scenarios
  - Test API unavailable, database failure, WebSocket disconnection scenarios
  - _Requirements: 9.1, 9.2, 9.3_

- [x] 17. Implement user authentication (optional)
  - Create user registration endpoint POST /api/auth/register
  - Create user login endpoint POST /api/auth/login with JWT token generation
  - Create logout endpoint POST /api/auth/logout
  - Implement session management with JWT tokens
  - Add authentication middleware for protected endpoints
  - Associate predictions with authenticated user accounts
  - Support anonymous users with browser session storage (frontend)
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 17.1 Write property test for user registration and authentication
  - **Property 29: User registration and authentication**
  - **Validates: Requirements 10.1, 10.2**

- [x] 17.2 Write property test for authenticated prediction association
  - **Property 30: Authenticated prediction association**
  - **Validates: Requirements 10.3**

- [x] 17.3 Write property test for anonymous user session storage
  - **Property 31: Anonymous user session storage**
  - **Validates: Requirements 10.4**

- [x] 17.4 Write property test for session cleanup on logout
  - **Property 32: Session cleanup on logout**
  - **Validates: Requirements 10.5**

- [x] 18. Implement frontend state manager
  - Create JavaScript state management module for application state
  - Implement mode switching logic (live vs simulated)
  - Add state persistence to localStorage
  - Implement state restoration on page load
  - _Requirements: 1.6, 12.1, 12.3_

- [x] 18.1 Write property test for view state preservation
  - **Property 2: View state preservation during mode switching**
  - **Validates: Requirements 1.6, 12.3**

- [x] 19. Implement frontend WebSocket client
  - Create WebSocket client module with connect, disconnect, send, subscribe methods
  - Implement automatic reconnection with exponential backoff
  - Add connection status indicator in UI
  - Implement message queuing during disconnection
  - Handle WebSocket events for live updates, chat messages, reactions
  - _Requirements: 1.2, 9.2_

- [x] 20. Implement frontend live match display
  - Create UI components for displaying live match data
  - Implement real-time score updates via WebSocket
  - Add match status indicators (live, completed, scheduled)
  - Display current batsmen, bowlers, and scores
  - Implement mode switching UI control
  - _Requirements: 1.5, 12.1, 12.4_

- [x] 21. Implement frontend match schedule and history views
  - Create schedule view showing upcoming matches
  - Create history view showing completed matches
  - Implement match highlights timeline component
  - Add date filtering and sorting
  - _Requirements: 2.1, 2.2, 2.3, 2.5_

- [x] 22. Implement frontend prediction UI
  - Create prediction input component for ball-by-ball predictions
  - Implement prediction submission via REST API
  - Display prediction history with accuracy statistics
  - Show leaderboard with filtering options (live, simulated, combined)
  - Display XP and streak information
  - _Requirements: 3.1, 3.2, 3.5, 3.6, 3.7_

- [x] 23. Implement frontend chat interface
  - Create chat room UI component
  - Implement real-time message display via WebSocket
  - Add message input with rate limiting feedback
  - Implement emoji reaction picker for ball events
  - Display aggregated reaction counts
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 24. Implement frontend poll interface
  - Create poll display component
  - Implement poll response submission
  - Display real-time poll results
  - _Requirements: 5.5_

- [x] 25. Implement frontend user profile view
  - Create profile page showing user statistics
  - Display earned achievement badges
  - Show prediction history with filtering
  - _Requirements: 5.7_

- [x] 26. Implement frontend data visualizations
  - Create momentum graph component using Chart.js or D3.js
  - Implement run rate comparison chart
  - Create wagon wheel visualization for batsmen
  - Implement manhattan chart for batsmen
  - Create bowling analysis visualization
  - Implement win probability timeline
  - Ensure all charts update in real-time with match data
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 27. Implement responsive design
  - Add CSS media queries for screen sizes 320px to 2560px
  - Optimize layout for mobile devices with touch interactions
  - Ensure charts scale appropriately on mobile
  - Test and fix mobile keyboard input issues in chat
  - _Requirements: 11.1, 11.2, 11.4, 11.5_

- [x] 28. Implement frontend error handling
  - Add error display components (toast notifications, modal dialogs)
  - Implement connection status indicators
  - Add fallback UI for when live scores are unavailable
  - Display user-friendly error messages for all error scenarios
  - _Requirements: 9.1, 9.4_

- [x] 29. Checkpoint - Ensure frontend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 30. Integration and wiring
  - Wire Live Match Service to WebSocket server for broadcasting updates
  - Connect Prediction Service to achievement badge system
  - Integrate Statistics Service with match completion events
  - Wire frontend components to backend API endpoints
  - Connect WebSocket client to all real-time features
  - Implement automatic fallback to simulated matches when no live matches available
  - _Requirements: 1.3, 1.7, 3.7, 4.3, 12.5_

- [x] 30.1 Write integration tests for end-to-end flows
  - Test complete user flow: view match → predict → earn XP → check leaderboard
  - Test mode switching with state preservation
  - Test error recovery scenarios
  - _Requirements: 1.6, 9.1, 12.3_

- [x] 31. Final checkpoint - Comprehensive testing
  - Run all unit tests and property tests
  - Perform manual testing on multiple devices and browsers
  - Test WebSocket reconnection behavior
  - Verify responsive design on mobile devices
  - Test error handling and fallback mechanisms
  - Ensure all tests pass, ask the user if questions arise.

- [x] 32. UI Enhancement and Polish
  - Refactor and enhance the overall UI design for a cleaner, more modern appearance
  - Improve color scheme and typography for better readability
  - Add smooth transitions and animations for better user experience
  - Enhance component layouts and spacing for visual consistency
  - Improve button styles, form inputs, and interactive elements
  - Add loading states and skeleton screens for better perceived performance
  - Optimize visual hierarchy and information architecture
  - Ensure consistent styling across all pages and components
  - Add micro-interactions for user feedback
  - Polish all visual elements based on implemented functionality
  - _Requirements: 11.1, 11.2, 12.4_

## Notes

- All tasks are required for comprehensive implementation with full test coverage
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation throughout implementation
- Property tests validate universal correctness properties with 100+ iterations
- Unit tests validate specific examples and edge cases
- The implementation follows an incremental approach: infrastructure → live scores → predictions → social → visualization → integration
- Authentication (task 17) is optional but recommended for production deployment
- Frontend uses vanilla JavaScript as specified in the existing project
- Backend uses FastAPI with Python as specified in the existing project
