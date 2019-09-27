from ascend import game


game.create_players()
game.world.spawn_mobs(num=20)

game.run()
