# Flatmate - Property Rental Platform

A comprehensive Flask-based web application for managing rental properties in Himachal Pradesh, India. This platform helps landlords and tenants connect, manage rental agreements, and handle property-related documentation.

## Features

- **Property Listings**: Browse rental properties across multiple cities in Himachal Pradesh
- **User Authentication**: Secure user registration and login
- **Rent Agreements**: Generate and manage rental agreements
- **Rent Receipts**: Create and track rent payment receipts
- **Property Verification**: Verify property details and landlord information
- **Visit Requests**: Schedule and manage property visit requests
- **Contact Management**: Submit and track contact inquiries
- **Premium Listings**: Premium property features for enhanced visibility

## Supported Cities

Shimla, Dharamshala, Manali, Kangra, Palampur, Chamba, Bilaspur, Sundernagar, Nurpur, Hamirpur, Solan, Kullu, Mandi, Baddi, Nahan, Paonta, Yol, Una, and more.

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML, CSS, JavaScript
- **Email**: Flask-Mail with Gmail SMTP

## Installation

### Prerequisites

- Python 3.7+
- pip (Python package installer)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/flatmate.git
   cd flatmate
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and fill in your configuration:
   - Gmail credentials (for email notifications)
   - Flask secret key
   - Database URI (if using a different database)
   - `DATABASE_URL` is also supported for cloud providers and Vercel deployments

5. **Run the application**
   ```bash
   python main.py
   ```

   The application will be available at `http://127.0.0.1:5000`

## Project Structure

```
flatmate/
├── main.py                 # Main Flask application
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── data.json              # Property listings data
├── users.json             # User data
├── premium_data.json      # Premium property listings
├── static/                # Static files
│   ├── css/               # Stylesheets
│   ├── images/            # Images (city and property photos)
│   └── uploads/           # User uploads
├── templates/             # HTML templates
└── instance/              # Flask instance folder (local)
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Flask
FLASK_ENV=development
FLASK_DEBUG=0

# Email (Gmail)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=465
MAIL_USE_SSL=1
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

**Note**: For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password.

## Database

The application uses SQLite by default. The database file (`himrooms.db`) is created automatically on first run.

### Database Models

- **ContactMessage**: Store contact form submissions
- **RentAgreement**: Store rental agreement details
- **VisitRequest**: Track property visit requests
- **RentReceipt**: Store generated rent receipts
- **VerificationRequest**: Store property/owner verification requests
- **ApplyInterest**: Track user interest in properties

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Security Note

- Never commit `.env` files with real credentials
- Use strong secret keys in production
- Enable HTTPS in production
- Validate and sanitize all user inputs
- Keep dependencies updated

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions, please create an issue on the GitHub repository.

---

**Developer**: Shaqueel
**Last Updated**: May 2026
