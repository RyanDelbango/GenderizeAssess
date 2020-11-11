from genderize import Genderize, GenderizeException
import csv
import sys
import os.path
import time
import argparse
import logging
import pandas

import jpyhelper as jpyh

def genderize(args):
    print(args)

    #File initialization
    dir_path = os.path.dirname(os.path.realpath(__file__))
    
    logging.basicConfig(filename=dir_path + os.sep + "log.txt", level=logging.DEBUG,
                        format= "%(asctime)s %(levelname)s %(name)s %(message)s" )
    logger=logging.getLogger(__name__)

    ofilename, ofile_extension = os.path.splitext(args.output)

    ofile = ofilename + "_" + time.strftime("%Y%m%d-%H%M%S") + ".csv"
    ifile = args.input

    if os.path.isabs(ifile):
        print("\n--- Input file: " + ifile)
    else:
        print("\n--- Input file: " + dir_path + os.sep + ifile)

    if os.path.isabs(ofile):
        print("--- Output file: " + ofile)
    else:
        print("--- Output file: " + dir_path + os.sep + ofile + "\n")

    #File integrity checking
    if not os.path.exists(ifile):
        print("--- Input file does not exist. Exiting.\n")
        sys.exit()

    #Some set up stuff
    ##csv.field_size_limit(sys.maxsize)

    #Initialize API key
    if not args.key == "NO_API":
        print("--- API key: " + args.key + "\n")
        genderize = Genderize(
            user_agent='GenderizeDocs/0.0',
            api_key=args.key)
        key_present = True
    else:
        print("--- No API key provided.\n")
        key_present = False

    #Read CSV into pandas dataframe        
    df = pandas.read_csv(ifile)
    first_name = df.first_name.to_list()

    o_first_name = list()
    for l in first_name:
        for b in l:
            o_first_name.append(b)

    if args.auto == True:
        uniq_first_name = list(set(o_first_name))
        chunks = list(jpyh.splitlist(uniq_first_name, 10));
        print("--- Read CSV with " + str(len(first_name)) + " first_name. " + str(len(uniq_first_name)) + " unique.")
    else:
        chunks = list(jpyh.splitlist(first_name, 10));
        print("--- Read CSV with " + str(len(first_name)) + " first_name")

    print("--- Processed into " + str(len(chunks)) + " chunks")

    if jpyh.query_yes_no("\n---! Ready to send to Genderdize. Proceed?") == False:
        print("Exiting...\n")
        sys.exit()

    if os.path.isfile(ofile):
        if jpyh.query_yes_no("---! Output file exists, overwrite?") == False:
            print("Exiting...\n")
            sys.exit()
        print("\n")

    if args.auto == True:
        ofile = ofile + ".tmp"

    response_time = [];
    gender_responses = list()
    #initialize lists for data references
    names = []
    gender = []
    probability = []
    count = []
    with open(ofile, 'w', newline='', encoding="utf8") as f:
        chunks_len = len(chunks)
        stopped = False
        for index, chunk in enumerate(chunks):
            if stopped:
                break
            success = False
            while not success:
                try:
                    start = time.time()

                    if key_present:
                        dataset = genderize.get(chunk)
                    else:
                        dataset = Genderize().get(chunk)

                    gender_responses.append(dataset)
                    success = True
                except GenderizeException as e:
                    #print("\n" + str(e))
                    logger.error(e)

                    #Error handling
                    if "response not in JSON format" in str(e) and args.catch == True:
                        if jpyh.query_yes_no("\n---!! 502 detected, try again?") == True:
                            success = False
                            continue
                    elif "Invalid API key" in str(e) and args.catch == True:
                        print("\n---!! Error, invalid API key! Check log file for details.\n")
                    else:
                        print("\n---!! GenderizeException - You probably exceeded the request limit, please add or purchase a API key. Check log file for details.\n")
                    stopped = True
                    break

                response_time.append(time.time() - start)
                print("Processed chunk " + str(index + 1) + " of " + str(chunks_len) + " -- Time remaining (est.): " + \
                    str( round( (sum(response_time) / len(response_time) * (chunks_len - index - 1)), 3)) + "s")




 

                for i in range(len(dataset)):
                    names.append(list(dataset[i].values())[0])
                    gender.append(list(dataset[i].values())[1])
                    probability.append(list(dataset[i].values())[2])
                    count.append(list(dataset[i].values())[3])




                        
                break

        #initialize lists for new columns
        genderFinal = []
        probabilityFinal = []
        countFinal = []

        #fill lists to match csv file while referencing info from the first lists
        for i in range(len(df)):
            genderFinal.append(gender[names.index(df.loc[i, "first_name"])])
            probabilityFinal.append(probability[names.index(df.loc[i, "first_name"])])
            countFinal.append(count[names.index(df.loc[i, "first_name"])])

        #add new columns to the data frame and convert to csv
        df["gender"] = genderFinal
        df["probability"] = probabilityFinal
        df["count"] = countFinal
        df.to_csv(ofile, index= False, index_label= False, float_format='%.0f')

        if args.auto == True:
            print("\nCompleting identical first_name...\n")
                #AUTOCOMPLETE first_name

                #Create master dict
            gender_dict = dict()
            for response in gender_responses:
                for d in response:
                    gender_dict[d.get("name")] = [d.get("gender"), d.get("probability"), d.get("count")]


        print("Done!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Bulk genderize.io script')
    required = parser.add_argument_group('required arguments')

    required.add_argument('-i','--input', help='Input file name', required=True)
    required.add_argument('-o','--output', help='Output file name', required=True)
    parser.add_argument('-k','--key', help='API key', required=False, default="NO_API")
    parser.add_argument('-c','--catch', help='Try to handle errors gracefully', required=False, action='store_true', default=True)
    parser.add_argument('-a','--auto', help='Automatically complete gender for identical first_name', required=False, action='store_true', default=False)
    parser.add_argument('-nh','--noheader', help='Input has no header row', required=False, action='store_true', default=False)

    genderize(parser.parse_args())
