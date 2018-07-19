from . import db

class Feed(db.Model):
    __tablename__ = 'feed'
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String, unique=True, index=True)
    etag = db.Column(db.String)
    last_modified = db.Column(db.String)
    last_published_element = db.Column(db.DateTime)
    content = db.Column(db.Text)


    def __repr__(self):
            return '<Feed #%s: %r last updated %s>' % (self.id, self.url, self.last_published_element)

class Episode(db.Model):
    __tablename__ = 'episode'
    id = db.Column(db.Integer, primary_key=True)
    published = db.Column(db.DateTime)
    content = db.Column(db.Text)
    feed_id = db.Column(db.Integer, db.ForeignKey('feed.id'), index=True)
    enclosure_url = db.Column(db.Text)
    enclosure_is_active = db.Column(db.Boolean, index=True)
    # Use cascade='delete,all' to propagate the deletion of a Feed onto its Employees
    feed = db.relationship('Feed',
                    backref = db.backref('episodes',
                                     uselist=True,
                                     cascade='delete,all'))



    # def __repr__(self):
    #         return '<Episode from feed #%s: %r>' % (self.feed_id, self.content)
