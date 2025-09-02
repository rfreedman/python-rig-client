#! env python3

#freq = "14074000" # to be formatted as "14.074.00"
#freq = "7074000" # to be formatted as "7.074.00"

freq = "14074120"

def format_freq():
    # last 2 chars
    # previous 3 chars
    # whatever is left at the beginning (1 or 2 chars)
    # {beginning}.{previous3}.{last2}
    freq_len = len(freq) # 7 or 8

    print(f"formatting '{freq}' with length {freq_len}")

    match freq_len:
        case 7:
            beginning = freq[0:1] 
        case 8:
            beginning = freq[0:2]

    middle = freq[-6:-3]

    end = freq[-3:]
    # print(f"last char is {end[-1:]}")
    #print(f"all but last char of 'end' is {end[:-1]}")
    while end[-1:] == '0':
        end = end[:-1]

    formatted = f"{beginning}.{middle}"
    if len(end) > 0:
        formatted = f"{formatted}.{end}"

    print(formatted)

format_freq()