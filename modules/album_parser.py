import json


def parse_album_idea(service, album_idea, track_count):

    prompt = f"""
You are an Album Creation Assistant.

Extract the user's album idea into clean JSON.

Return ONLY valid JSON.

Required fields:

album_title
album_story
genre
track_count
special_notes
final_emotion

Use track count: {track_count}

Album Idea:

{album_idea}
"""

    result = service.ask(prompt)

    return json.loads(result)