CREATE TABLE Users (
    uid SERIAL PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    nickname VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Workspaces (
    wid SERIAL PRIMARY KEY,
    wname VARCHAR(100) NOT NULL,
    description TEXT,
    creator_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creator_id) REFERENCES Users(uid)
);

CREATE TABLE WorkspaceMembership (
    wid INT NOT NULL,
    uid INT NOT NULL,
    role VARCHAR(20) NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (wid, uid),
    FOREIGN KEY (wid) REFERENCES Workspaces(wid),
    FOREIGN KEY (uid) REFERENCES Users(uid),
    CHECK (role IN ('admin', 'member','role'))
);

CREATE TABLE WorkspaceInvitations (
    invite_id SERIAL PRIMARY KEY,
    wid INT NOT NULL,
    inviter_uid INT NOT NULL,
    invitee_uid INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP,
    FOREIGN KEY (wid) REFERENCES Workspaces(wid),
    FOREIGN KEY (inviter_uid) REFERENCES Users(uid),
    FOREIGN KEY (invitee_uid) REFERENCES Users(uid),
    CHECK (status IN ('accepted', 'pending', 'rejected'))
);

CREATE TABLE Channels (
    cid SERIAL PRIMARY KEY,
    wid INT NOT NULL,
    cname VARCHAR(100),
    ctype VARCHAR(20) NOT NULL,
    creator_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wid) REFERENCES Workspaces(wid),
    FOREIGN KEY (creator_id) REFERENCES Users(uid),
    CHECK (ctype IN ('public', 'private', 'direct'))
);

CREATE TABLE ChannelMembers (
    cid INT NOT NULL,
    uid INT NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (cid, uid),
    FOREIGN KEY (cid) REFERENCES Channels(cid),
    FOREIGN KEY (uid) REFERENCES Users(uid)
);

CREATE TABLE ChannelInvitations (
    invite_id SERIAL PRIMARY KEY,
    cid INT NOT NULL,
    inviter_uid INT NOT NULL,
    invitee_uid INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP,
    FOREIGN KEY (cid) REFERENCES Channels(cid),
    FOREIGN KEY (inviter_uid) REFERENCES Users(uid),
    FOREIGN KEY (invitee_uid) REFERENCES Users(uid),
    CHECK (status IN ('accepted', 'pending', 'rejected'))
);

CREATE TABLE Messages (
    mid SERIAL PRIMARY KEY,
    cid INT NOT NULL,
    sender_id INT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cid) REFERENCES Channels(cid),
    FOREIGN KEY (sender_id) REFERENCES Users(uid)
);


INSERT INTO Users (email, username, nickname, password_hash)
VALUES
('john@example.com', 'john', 'John', 'hash_john'),
('emma@example.com', 'emma', 'Emma', 'hash_emma'),
('linda@example.com', 'linda', 'Linda', 'hash_linda'),
('susan@example.com', 'susan', 'Susan', 'hash_susan'),
('noah@example.com', 'noah', 'Noah', 'hash_noah');


INSERT INTO Workspaces (wname, description, creator_id)
VALUES
('Math Club', 'Math workspace', 1),
('CS Club', 'CS workspace', 5);

INSERT INTO WorkspaceMembership (wid, uid, role)
VALUES
(1, 1, 'creator'),
(1, 2, 'admin'),
(1, 3, 'member'),
(1, 4, 'member'),
(2, 5, 'creator'),
(2, 2, 'member');


INSERT INTO WorkspaceInvitations
(wid, inviter_uid, invitee_uid, status, created_at, responded_at)
VALUES
(1, 1, 2, 'accepted', CURRENT_TIMESTAMP - INTERVAL '20 days', CURRENT_TIMESTAMP - INTERVAL '19 days'),
(1, 1, 3, 'accepted', CURRENT_TIMESTAMP - INTERVAL '18 days', CURRENT_TIMESTAMP - INTERVAL '17 days'),
(1, 1, 4, 'accepted', CURRENT_TIMESTAMP - INTERVAL '16 days', CURRENT_TIMESTAMP - INTERVAL '15 days'),
(2, 5, 2, 'accepted', CURRENT_TIMESTAMP - INTERVAL '10 days', CURRENT_TIMESTAMP - INTERVAL '9 days'),
(2, 5, 4, 'rejected', CURRENT_TIMESTAMP - INTERVAL '6 days', CURRENT_TIMESTAMP - INTERVAL '5 days');

INSERT INTO Channels (wid, cname, ctype, creator_id)
VALUES
(1, 'general-public', 'public', 1),
(1, 'geometry-public', 'public', 1),
(1, 'project-private', 'private', 1),
(1, 'john-emma-dm', 'direct', 1),
(2, 'cs-public', 'public', 5);

INSERT INTO ChannelMembers (cid, uid)
VALUES
(1, 1),
(1, 2),
(1, 3),
(2, 1),
(2, 3),
(3, 1),
(3, 2),
(3, 3),
(4, 1),
(4, 2),
(5, 5),
(5, 2);

INSERT INTO ChannelInvitations
(cid, inviter_uid, invitee_uid, status, created_at, responded_at)
VALUES
(2, 1, 3, 'accepted', CURRENT_TIMESTAMP - INTERVAL '9 days', CURRENT_TIMESTAMP - INTERVAL '8 days'),
(2, 1, 2, 'pending', CURRENT_TIMESTAMP - INTERVAL '10 days', NULL),
(2, 1, 4, 'pending', CURRENT_TIMESTAMP - INTERVAL '2 days', NULL),
(3, 1, 2, 'accepted', CURRENT_TIMESTAMP - INTERVAL '9 days', CURRENT_TIMESTAMP - INTERVAL '8 days'),
(3, 1, 3, 'accepted', CURRENT_TIMESTAMP - INTERVAL '8 days', CURRENT_TIMESTAMP - INTERVAL '7 days');

INSERT INTO Messages (cid, sender_id, content, created_at)
VALUES
(1, 1, 'Welcome to the Math Club.', CURRENT_TIMESTAMP - INTERVAL '6 days'),
(1, 2, 'What is a perpendicular?', CURRENT_TIMESTAMP - INTERVAL '5 days'),
(1, 3, 'Perpendicular lines intersect at 90 degrees.', CURRENT_TIMESTAMP - INTERVAL '4 days'),
(2, 1, 'Let us discuss geometry today.', CURRENT_TIMESTAMP - INTERVAL '3 days'),
(2, 3, 'OK, so what is perpendicular bisector?', CURRENT_TIMESTAMP - INTERVAL '2 days'),
(3, 2, 'Could you give me some perpendicular example?', CURRENT_TIMESTAMP - INTERVAL '2 days'),
(3, 1, 'OK, here it is.', CURRENT_TIMESTAMP - INTERVAL '1 day'),
(5, 5, 'Welcome to CS club.', CURRENT_TIMESTAMP - INTERVAL '3 days'),
(5, 2, 'Let us discuss database today', CURRENT_TIMESTAMP - INTERVAL '2 days');