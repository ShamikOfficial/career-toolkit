-- Career Toolkit schema (ATS + CRM/outreach)
-- Create the database first (adjust name if desired):
--   CREATE DATABASE career_toolkit;
--   USE career_toolkit;

-- -----------------------
-- ATS: jobs + applications
-- -----------------------
CREATE TABLE IF NOT EXISTS jobs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  source_url TEXT NOT NULL,
  company VARCHAR(255) NULL,
  title VARCHAR(255) NULL,
  location VARCHAR(255) NULL,
  platform VARCHAR(100) NULL,
  job_description LONGTEXT NULL,
  parsed_keywords JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_jobs_source_url (source_url(512))
);

CREATE TABLE IF NOT EXISTS applications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  job_id INT NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'applied',
  resume_pdf_path TEXT NULL,
  cover_letter_path TEXT NULL,
  notes TEXT NULL,
  applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_applications_job
    FOREIGN KEY (job_id) REFERENCES jobs(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_applied_at ON applications(applied_at);

-- -----------------------
-- CRM/Outreach: contacts + messages
-- -----------------------
CREATE TABLE IF NOT EXISTS contacts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NULL,
  email VARCHAR(320) NOT NULL,
  linkedin_url TEXT NULL,
  company VARCHAR(255) NULL,
  notes TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_contacts_email (email)
);

CREATE TABLE IF NOT EXISTS application_contacts (
  application_id INT NOT NULL,
  contact_id INT NOT NULL,
  relationship VARCHAR(50) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (application_id, contact_id),
  CONSTRAINT fk_app_contacts_application
    FOREIGN KEY (application_id) REFERENCES applications(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_app_contacts_contact
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS outreach_messages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  application_id INT NOT NULL,
  contact_id INT NOT NULL,
  subject TEXT NOT NULL,
  body LONGTEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'draft', -- draft|sent|failed
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  sent_at DATETIME NULL,
  gmail_message_id VARCHAR(255) NULL,
  gmail_thread_id VARCHAR(255) NULL,
  error TEXT NULL,
  CONSTRAINT fk_outreach_application
    FOREIGN KEY (application_id) REFERENCES applications(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_outreach_contact
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_outreach_status ON outreach_messages(status);
CREATE INDEX idx_outreach_created_at ON outreach_messages(created_at);

