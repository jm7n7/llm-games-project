login_dict = {"player1":{"username":'Jack',
"password":'23'},
"player2":"Joseph"}


game_hist_dict = {"player_1":{"Game1":{"move_hist":['you found me'],
"knowledge_graph":'graph'},
"Game2":{"move_hist":['you found me'],
"knowledge_graph":'graph'}
}
}
import json

with open("game_hist_dict.json", "w") as f:
json.dump(game_hist_dict, f, indent=2)


user = login_dict["player1"]
game_hist_dict["player_1"]["Game1"]['move_hist']