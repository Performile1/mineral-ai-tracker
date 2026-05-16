# Deployment Guide

## Local Development with Docker (Recommended)

### Prerequisites
- Docker Desktop installed
- Python 3.10+
- Node.js 18+

### Quick Start with Docker

1. **Start PostgreSQL with Docker**
   ```bash
   docker-compose up -d
   ```

2. **Verify PostgreSQL is running**
   ```bash
   docker-compose ps
   ```

3. **Apply Database Schema**
   ```bash
   # The schema is automatically applied via docker-compose
   # Or manually apply:
   docker exec -it mineral-ai-postgres psql -U mineral_user -d mineral_ai_tracker -f /docker-entrypoint-initdb.d/schema.sql
   ```

4. **Backend Setup**
   ```bash
   cd backend
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Configure environment
   cp .env.example .env
   # DATABASE_TYPE is already set to "local" in .env.example
   
   # Run scheduler
   python scheduler.py
   ```

5. **Frontend Setup**
   ```bash
   cd frontend
   
   # Install dependencies
   npm install
   
   # Configure environment
   cp .env.example .env.local
   # NEXT_PUBLIC_DATABASE_TYPE is already set to "local"
   
   # Run development server
   npm run dev
   ```

### Docker Commands

```bash
# Start PostgreSQL
docker-compose up -d

# Stop PostgreSQL
docker-compose down

# View logs
docker-compose logs -f postgres

# Restart PostgreSQL
docker-compose restart postgres

# Access PostgreSQL directly
docker exec -it mineral-ai-postgres psql -U mineral_user -d mineral_ai_tracker

# Backup database
docker exec mineral-ai-postgres pg_dump -U mineral_user mineral_ai_tracker > backup.sql

# Restore database
docker exec -i mineral-ai-postgres psql -U mineral_user -d mineral_ai_tracker < backup.sql
```

## Production Deployment Options

### Option 1: Supabase Cloud (Alternative)

If you prefer to use Supabase instead of local Docker:

1. **Create Supabase Project**
   - Go to supabase.com
   - Create new project
   - Note project URL and keys

2. **Apply Schema**
   - Open SQL Editor in Supabase
   - Copy contents of `supabase/schema.sql`
   - Execute

3. **Update Environment Variables**
   ```bash
   # backend/.env
   DATABASE_TYPE=supabase
   SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   ```

### Option 2: Vercel Serverless (Backend)

**Prerequisites**
- Vercel account
- Supabase project or external PostgreSQL

**Steps**

1. **Environment Variables in Vercel**
   ```
   DATABASE_TYPE=supabase
   SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   TWILIO_PHONE_NUMBER=your_twilio_number
   ```

2. **API Structure**
   ```
   api/
   ├── [feature]/
   │   ├── endpoint1.ts
   │   └── endpoint2.ts
   └── lib/
       └── db.ts
   ```

3. **Scheduler Considerations**
   - Vercel serverless functions have execution time limits
   - For long-running scrapers, consider:
     - Using Vercel Cron Jobs
     - Moving scheduler to a separate service (e.g., Railway, Render)
     - Using Supabase Edge Functions for scheduled tasks

### Frontend Deployment (Vercel)

**Steps**

1. **Build Configuration**
   ```bash
   npm run build
   ```

2. **Environment Variables in Vercel**
   ```
   NEXT_PUBLIC_DATABASE_TYPE=supabase
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
   NEXT_PUBLIC_API_URL=your_api_url
   ```

3. **Deploy**
   ```bash
   vercel --prod
   ```

## Database Setup

### Local PostgreSQL (Docker)
- Automatically configured via docker-compose
- Schema applied on container initialization
- Data persisted in Docker volume

### Supabase (Alternative)
- Create project at supabase.com
- Apply schema via SQL Editor
- RLS policies included in schema
- Extensions: uuid-ossp, pgcrypto

## Monitoring & Logging

### Backend
- Loguru configured for structured logging
- Error logs: `logs/errors.log`
- Crash dumps: `logs/crash_dump.log`
- Scraper logs: `logs/scraper.log`

### Frontend
- Browser console for client-side errors
- Vercel Analytics for deployment monitoring

### Docker
- Container health checks
- Log aggregation via docker-compose logs

## Backup Strategy

### Local PostgreSQL (Docker)
```bash
# Backup
docker exec mineral-ai-postgres pg_dump -U mineral_user mineral_ai_tracker > backup.sql

# Restore
docker exec -i mineral-ai-postgres psql -U mineral_user -d mineral_ai_tracker < backup.sql

# Backup volume
docker run --rm -v mineral-ai-postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_data.tar.gz /data
```

### Supabase (Alternative)
- Supabase provides automated backups
- Point-in-time recovery available

## Scaling Considerations

### Scraping
- Proxy rotation to avoid IP blocking
- Rate limiting on all external APIs
- Consider distributed scraping for high-volume needs

### Database
- **Local Docker**: Scale by upgrading container resources
- **Supabase**: Auto-scales PostgreSQL
- Monitor connection pool usage
- Consider read replicas for heavy read loads

### Frontend
- Vercel auto-scales Next.js
- Image optimization for logos/charts
- Consider CDN for static assets

## Security Checklist

- [ ] All environment variables set
- [ ] DATABASE_TYPE configured correctly
- [ ] RLS policies enabled and tested (if using Supabase)
- [ ] PostgreSQL credentials secure (local Docker)
- [ ] Service role keys only on backend (if using Supabase)
- [ ] HTTPS enforced (production)
- [ ] Rate limiting configured
- [ ] Error handling tested
- [ ] Backup strategy in place
- [ ] Monitoring configured

## Troubleshooting

### Common Issues

**Docker PostgreSQL not starting**
```bash
# Check logs
docker-compose logs postgres

# Remove volume and restart
docker-compose down -v
docker-compose up -d
```

**Scraper failing**
- Check proxy configuration
- Verify rate limits
- Check source website structure hasn't changed

**Database connection errors**
- Verify DATABASE_TYPE in .env
- Check PostgreSQL is running (docker-compose ps)
- Verify credentials
- Check network connectivity

**SMS not sending**
- Verify Twilio credentials
- Check phone number format
- Review Twilio account balance

**Frontend build errors**
- Run `npm install` to ensure dependencies
- Check TypeScript errors
- Verify environment variables
