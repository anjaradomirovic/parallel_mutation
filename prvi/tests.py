from pareto import pareto_ranks, crowding_distance

# rangovi
scores = [(8,7,6), (5,4,3), (9,3,8), (6,6,6)]
rangovi = pareto_ranks(scores)
assert rangovi[(8,7,6)] == 1
assert rangovi[(9,3,8)] == 1
assert rangovi[(6,6,6)] == 2
assert rangovi[(5,4,3)] == 3

# crowding
sloj = [(9,1,9), (7,3,7), (3,7,3), (1,9,1)]
cd = crowding_distance(sloj)
assert cd[(9,1,9)] == float('inf')
assert cd[(1,9,1)] == float('inf')
assert cd[(7,3,7)] != float('inf')
assert cd[(3,7,3)] != float('inf')

print("Svi testovi prolaze.")