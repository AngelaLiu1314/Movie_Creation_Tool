# Posterizer.ai

## Database
This database is a crucial part of our final project designed to generate movie posters based on plot input. The system manages movie data using MongoDB, where each movie's metadata—such as title, rating, genre, director, actors, and plot—is stored in a `MovieDetail` collection. The ultimate goal is to feed movie plots into a custom algorithm that generates corresponding movie posters, using descriptive key phrases associated with each movie.

### Data Model
The `MovieDetail` collection in the `Movies` database has the following structure:

```json
{
  "imdb_id": "string",          // The unique IMDb ID for the movie.
  "title": "string",            // The movie's title.
  "Rating": "string",           // The movie's rating (e.g., PG-13, R).
  "RTM": "string",              // Rotten Tomatoes score or related metric.
  "DOR": "string",              // Date of Release.
  "Genre": ["string"],          // An array of genres the movie belongs to.
  "Director": "string",         // The director of the movie.
  "Writer(s)": ["string"],      // An array of writers involved.
  "Actors": [{"Actor 1": "string", "Actor 2": "string", ...}], // Actors and their roles.
  "Plot": "string",             // A brief description of the plot.
  "Estimated Budget": "string", // Estimated budget of the movie.
  "Poster": "string",           // URL or location of the movie poster.
  "Poster Key Characteristics": {JSON object generated from GPT prompt} // Descriptive key characteristics for the movie poster.
}
```

### Reason for Choosing MongoDB
MongoDB was selected for its flexibility in handling unstructured and semi-structured data. Movie metadata can be complex and diverse, including nested objects (e.g., actors, writers) and arrays (e.g., genres), and MongoDB’s schema-less design allows for this variability without rigid table structures like SQL databases.

Additionally, MongoDB allows for rapid iteration and evolution of the data model, making it ideal for handling the dynamic nature of this project, especially as we work toward integrating movie plot-based poster generation.

### Database Configuration
1. **Collaborator Access:**
   - Admin adds collaborators as necessary in MongoDB Atlas.
   - Once added, each member can generate their own MongoDB connection string via MongoDB Atlas. This will ensure that team members can independently connect to the shared database.

2. **Configure Environment Variables:**
   - Once the connection string acquired, create a `.env` file in the project root directory.
   - Add your MongoDB Atlas connection string (URI) to this file:
     ```
     MONGODB_URI=mongodb+srv://<username>:<password>@movies.7r39n.mongodb.net/
     ```
   - Replace `<username>` and `<password>` with your credentials.

3. **Run the Top Snippet to Connect to the Database:**
   - Use the provided database connection code snippet from the main project (as in the example below) to verify the connection and begin interacting with the database.
   ```python
   import os
   from dotenv import load_dotenv
   import pymongo
   
   load_dotenv()
   mongodb_uri = os.getenv('MONGODB_URI')

   try:
      client = pymongo.MongoClient(mongodb_uri) # this creates a client that can connect to our DB
      db = client.get_database("movies") # this gets the database named 'Movies'
      movieDetails = db.get_collection("movieDetails")

      client.server_info() # forces client to connect to server
      print("Connected successfully to the 'Movies' database!")

   except pymongo.errors.ConnectionFailure as e:
      print(f"Could not connect to MongoDB: {e}")
      exit(1)
   ```

4. **Database Design:**
   - The database contains a `Movies` database with a `MovieDetails` collection, where each document represents a movie and its associated metadata such as plot, rating, genre, actors, and key phrases for poster generation.

5. **Populating the Database:**
   - Data insertion into the `MovieDetails` collection is done either manually or through automated scripts. The system will later integrate modules for generating movie posters based on plot descriptions.

## API