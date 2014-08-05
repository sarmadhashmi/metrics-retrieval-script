# Sarmad Hashmi
# July 22, 2014

import pymysql
import json
import re
from collections import defaultdict
import csv
import time
import sys
from Tkinter import *
import Tkinter as tk
import ttk
from collections import Counter
import os

CONFIG = open('./config.json').read()
CONFIG = json.loads(CONFIG)
connection = pymysql.connect(**CONFIG)
connection2 = pymysql.connect(**CONFIG)
cursor = connection.cursor()
other_cursor = connection2.cursor()
dir_name= ''
main_file = ''
main_writer = ''

class Table:
    def __init__(self, table_name, tk=None,x=None,y=None):
        try:
            self.table_name = table_name
            self.options = ["Sort By"]
            self.files = {}
            self.writers = {}
            self.constants = {"is_dynamic":{1:"DYNAMIC",0:"STATIC"}, "state":{1: 'EXPIRED', 2: 'GRACE' , 3: 'APPEARS', 4: 'DISABLED', 5:'ACTIVE'}}
            other_cursor.execute("SHOW COLUMNS FROM {}".format(table_name))
            for j in other_cursor:
                self.options.append(j[0])            
            self.selected_option = StringVar()
            self.checkbox_state = IntVar()
            self.create_checkbox_for_table(tk, x, y)
            self.create_dropdown_for_options(tk, x, y+1)
            self.custom_options = {}
        except Exception as e:
            print(str(e) + ' ---- line #: ' + str(sys.exc_traceback.tb_lineno))
            
    def create_dropdown_for_options(self, tk, x, y):
        self.optionMenu = OptionMenu(tk, self.selected_option, *self.options)
        self.optionMenu.grid(row=x,column=y, sticky=E)
        self.selected_option.set(self.options[0])

    def create_checkbox_for_table(self, tk, x, y):
        Checkbutton(tk, text="Total # of {}".format(self.table_name), variable=self.checkbox_state).grid(row=x,column=y, sticky=W)

    def get_checkbox_state(self):
        return self.checkbox_state.get()

    def get_dropdown_option(self):
        return self.selected_option.get()

    def get_custom_options(self):
        return self.custom_options.keys()
    
    def add_to_options(self, options):
        for i in options:
            for k in i:                
                self.optionMenu['menu'].add_command(label=k, command=tk._setit(self.selected_option, k))
                self.custom_options[k] = i[k]
            
    def get_count_for_custom_col(self, companies=[],company_public_ids=None, custom_name=None):        
        o = self.custom_options[custom_name]
        if o['json']:
            if 'regexp' in o:
                if 'length' in o:
                    c = [s + '_length' for s in o['parse'].split(',')]
                    self.get_count_from_json_col(o['col_name'],c, o['regexp'], companies,company_public_ids, o['length'])
                else:
                    self.get_count_from_json_col(o['col_name'],o['parse'].split(','), o['regexp'], companies,company_public_ids)
            else:
                self.get_count_from_json_col(o['col_name'],o['parse'].split(','), None, companies,company_public_ids)
                
    
    def get_count(self, companies=[], company_public_ids = None, col_name = None):
        companies_string = ', '.join(str(v) for v in companies)        
        if not companies:
            companies_string = 'SELECT id FROM company'        
        if col_name and col_name != "Sort By":
            self.create_file_and_writer(col_name)
            if 'date' in col_name and 'company_id' in self.options:
                query = "SELECT DATE({}),COUNT(*) as count FROM {} WHERE company_id IN ({}) GROUP BY DATE({}) ORDER BY DATE({}) DESC".format(col_name, self.table_name, companies_string, col_name,col_name)
            elif 'date' in col_name:
                query = "SELECT DATE({}),COUNT(*) as count FROM {} GROUP BY DATE({}) ORDER BY DATE({}) DESC".format(col_name, self.table_name, col_name,col_name)
            elif "company_id" in self.options:
                query = "SELECT {},COUNT(*) as count FROM {} WHERE company_id IN ({}) GROUP BY {} ORDER BY count DESC".format(col_name, self.table_name, companies_string, col_name)
            elif self.table_name == "company":
                query = "SELECT {},COUNT(*) as count FROM {} WHERE id IN ({}) GROUP BY {} ORDER BY count DESC".format(col_name, self.table_name, companies_string, col_name)
            else:
                query = "SELECT {},COUNT(*) as count FROM {} GROUP BY {} ORDER BY count DESC".format(col_name, self.table_name, col_name)
            cursor.execute(query)
            for row in cursor:
                c = row[0]
                if col_name in self.constants:
                    c = self.constants[col_name][c]                
                if companies[0]==row[0]:
                    self.writers[col_name].writerow(["{}:{}:{}:count".format(self.table_name, col_name,"PARTNER"), row[1]])
                elif col_name == "company_id":
                    if company_public_ids:
                        self.writers[col_name].writerow(["{}:{}:{}:count".format(self.table_name, col_name, company_public_ids[c]), row[1]])
                    else:
                        self.writers[col_name].writerow(["{}:{}:{}:count".format(self.table_name, col_name, c), row[1]])
                else:
                    self.writers[col_name].writerow(["{}:{}:{}:count".format(self.table_name, col_name,c), row[1]])
        if "company_id" in self.options:
            query = "SELECT COUNT(*) FROM {} WHERE company_id IN ({})".format(self.table_name, companies_string)
        elif self.table_name == "company":
            query = "SELECT COUNT(*) FROM {} WHERE id IN ({})".format(self.table_name, companies_string)
        else:
            query = "SELECT COUNT(*) FROM {}".format(self.table_name)
        cursor.execute(query)
        for row in cursor:
            main_writer.writerow(["{}:count".format(self.table_name), row[0]])

    def get_count_from_json_col(self, col_name,things_to_parse,reg = None, companies=[],company_public_ids = None, length=False):
        companies_string = ', '.join(str(v) for v in companies)
        query = ("SELECT {} FROM {} WHERE company_id IN ({})".format(col_name, self.table_name, companies_string))
        cursor.execute(query)
        counts = {}        
        for i in things_to_parse:
            self.create_file_and_writer(col_name, i)
            counts[i] = defaultdict(int)
        for c in cursor:
            try:
                json_schema = json.loads(c[0])
                for i in things_to_parse:
                    c = i
                    if '_length' in c:
                        c = c[:-7]
                    parsed = self.recursive_walk_through_json(json_schema, c)
                    if parsed:
                        try:
                            if not reg:
                                if not isinstance(counts[i], Counter):
                                    counts[i] = Counter()                                
                                counts[i] += Counter(parsed)
                            else:
                                raise Exception
                        except:
                            for p in parsed:                                
                                if length:
                                    counts[i][json_schema['id']] = len(p)
                                elif reg and not length:
                                    found = re.findall(reg,p)
                                    if found:                                        
                                        for f in found:                                            
                                            counts[i][f.lower()] += 1
            except Exception as e:
                print(e)
        for i in things_to_parse:
            s = col_name+">"+i            
            if isinstance(counts[i], Counter):
                for t in counts[i].most_common():
                    self.writers[s].writerow([t[0],t[1]])
            else:
                for d in sorted(counts[i], key=counts[i].get, reverse=True):
                    if companies[0]==d:
                        self.writers[s].writerow(["PARTNER",counts[i][d]])
                    else:
                        self.writers[s].writerow([d,counts[i][d]])
                    
        query = "SELECT COUNT(*) FROM {} WHERE company_id IN ({})".format(self.table_name, companies_string)
        cursor.execute(query)
        for row in cursor:
            main_writer.writerow(["{}:count".format(self.table_name), row[0]])
            
    def create_file_and_writer(self, col_name, json_field_name= None):
        s = col_name
        if json_field_name:
            s = col_name+">"+json_field_name            
            self.files[s] = file(dir_name+'/# of {} sorted by {}.csv'.format("klips", json_field_name), 'wb')
        else:
            self.files[s] = file(dir_name+'/# of {} sorted by {}.csv'.format(self.table_name, col_name), 'wb')
        self.writers[s] = csv.writer(self.files[s])
        outputted_files.append(self.files[s].name)
        
    def recursive_walk_through_json(self, n, k): 
        l =[]    
        try:
            if isinstance(n, dict):        
                for key, val in n.items():
                    if (key == k):
                        if (val and not k == 'formulas'):                        
                            l.append(val)
                        elif (val[0] and k == 'formulas'):                        
                            l.append(val[0]['txt'])
                        elif (val[0]):
                            l.append(val[0])
                        
                    else:
                         l = l + self.recursive_walk_through_json(val,k)
            elif isinstance(n, list):
                if (len(n)):
                    l = l + self.recursive_walk_through_json(n[0],k)
        except:
            pass    
        return l


    def close_all_files(self):
        for f in self.files:
            self.files[f].close()



def main():
    start = time.clock()
    partner = partnerID.get()    
    company_public_ids = {}
    companies = []
    global dir_name, main_file, main_writer
    
    if partner and not cid.get():
        cursor.execute("SELECT name FROM company WHERE public_id='{}'".format(partner))
        dir_name = cursor.fetchall()[0][0] + '-data'
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        if withoutPartner.get():
            query = "SELECT c.id, c.public_id FROM company c1 LEFT JOIN company c ON c.partner_parent_id = c1.id WHERE c1.public_id = '{}'".format(partner, partner)
        else:
            query = "SELECT c.id, c.public_id FROM company c1 LEFT JOIN company c ON(c.partner_parent_id = c1.id OR c.public_id = '{}') WHERE c1.public_id = '{}'".format(partner, partner)
    elif not partner and not cid.get():
        query = "SELECT id, public_id FROM company c"
    elif not partner and cid.get():
        ids = cid.get().split(', ')
        query = "SELECT id, public_id FROM company c WHERE c.public_id in ({})".format(', '.join('"{0}"'.format(id) for id in  ids))
    if activeOnly.get() and not(not partner and not cid.get()):
        query += " AND c.state = 5"  #only active companies
    cursor.execute(query)
    for item in cursor:
        companies.append(item[0])
        company_public_ids[item[0]] = item[1]
    if not dir_name:
        if not os.path.exists('data'):
            os.makedirs('data')
        dir_name = 'data'
    main_file = file(dir_name+'/main-data.csv','wb')
    main_writer = csv.writer(main_file)
    outputted_files.append(main_file.name)
    for t in tables:
        if t.get_checkbox_state():            
            if t.get_dropdown_option() in t.get_custom_options():
                t.get_count_for_custom_col(companies,company_public_ids, t.get_dropdown_option())
            elif t.get_dropdown_option():
                t.get_count(companies, company_public_ids, t.get_dropdown_option())
            else:
                t.get_count(companies, company_public_ids)
            t.close_all_files()
    main_file.close()
    end = time.clock()
    done = Label(text="DONE! It took: {} seconds.".format(end-start)).grid(row=last_row+1, column=1)
    del outputted_files[:]
    dir_name = None

if __name__ == "__main__":
    cursor.execute("SHOW TABLES")
    outputted_files = []
    tables = []
    master = Tk()
    
    partnerID = StringVar()
    cid = StringVar()
    withoutPartner = IntVar()
    activeOnly = IntVar()
    master.wm_title("KF stats")
    Label(text="Partner PUBLIC ID/Account #").grid(row=0, column=0)
    Label(text="Company PUBLIC IDs (seperated by commas)").grid(row=1, column=0)
    Checkbutton(master, text="Without Partner?", variable=withoutPartner).grid(row=0,column=2)
    Checkbutton(master, text="Only Active Companies?", variable=activeOnly).grid(row=0,column=3)
    partner = Entry(master, textvariable=partnerID, width=80).grid(row=0, column = 1)
    company = Entry(master, textvariable=cid, width=80).grid(row=1, column = 1)
   
    row = 2
    col=0
    i = 0
    for c in cursor:
        t = Table(c[0],master,row,col)
        tables.append(t)
        if c[0] == "klip":
            t.add_to_options([{"Klip Count By Type":{'col_name':'klipSchema','json':True,'parse':'type'}},{"Function Count By Type":{'col_name':'klipSchema','regexp':'([A-Za-z]+)(?:\()','json':True,'parse':'formulas'}},{"Formula Length By Klip":{'col_name':'klipSchema','regexp':'([A-Za-z]+)(?:\()','json':True,'parse':'formulas', 'length':True}}])
        row += 1
        i+=1
        if i>25:
            i=0
            last_row=row
            row= 2
            col=2
            break
    button = Button(master, text="Get Data", command=main).grid(row=last_row,column=1)
    master.mainloop()
