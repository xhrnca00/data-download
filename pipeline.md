# Pipeline

1. get csv (as file for now - requires authentication to GET)
1. parse CSV (create links to vehicle JSONs)
1. GET all JSONs ("callback": GET -> parse, save)
1. GET images ("callback": GET -> save)
   - preferably GET images and save them before getting all JSONs (crash -> less lost work)
