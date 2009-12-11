#!/usr/bin/python
import socket
import sys
import struct
import time
import xml.dom.minidom
import ftplib
import select

HOST = 'hbms.datavertex.com'
PORT = 20203

UPLOAD_TO_FTP = False
FTP_UPLOAD_HOST = 'FTP_SERVER'
FTP_UPLOAD_PORT = 21
FTP_UPLOAD_USER = 'FTP_USERNAME'
FTP_UPLOAD_PASS = 'FTP_PASSWORD'
FTP_UPLOAD_PATH = "/"
FTP_UPLOAD_FILE = "servers.xml"

def DoTheEntireThing():
  
  # create the socket
  try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  except socket.error, msg:
    sys.stderr.write("Error: unable to create the socket : %s\n" % msg[1])
    return 1
  
  sock.settimeout(5.0)
  
  # connect to the master server
  try:
    sock.connect((HOST, PORT))
  except socket.error, msg:
    sys.stderr.write("Error: Unable to connect to the server: %s\n" % msg[1])
    return 2
  
  # receive the initial packet
  try:
    data = sock.recv(12)
  except socket.error, msg:
    sys.stderr.write("Error reading from socket: %s\n" % msg[1])
    return 3
  
  #make sure bytes 0-4 match up with expected
  if (data[0:4] != "HBSL"):
    sys.stderr.write("Unexpected token from host.")
    return 4
  
  # Decipher bytes 4 to 12 as two little-endian ints. 
  # according to the python docs, the '<' means little endian, I means a 32-bit (four byte) unsigned integer
  # unpack returns an array just like PHP does, but python lets you save members of an array
  # into variables immediately
  # I Could have easily done something like 
  # somearray = unpack(blah blah)
  # followed by 
  # magic_number = somearray[0] 
  # players_playing = somearray[1] 
  # python is better and cleaner than that...
  # data[4:12] just means use the 4th to the 12th bytes.  (Ie, skipping the "HBSL") 
  magic_number, players_playing = struct.unpack("<II",data[4:12])
  
  sys.stdout.write("Magic Number: %i\n" % magic_number)
  sys.stdout.write("Players Playing: %i\n" % players_playing)
  
  # ask the server for the full list of servers
  # we're sending the magic number as a little endian 4-byte int
  # followed by 4 characters: 255 0 0 0 as BYTES.
  
  responsepack = struct.pack("<IBBBB",magic_number,255,0,0,0)
  
  try:
    sock.send(responsepack)
  except socket.error, msg:
    sys.stderr.write("Error, unable to get server list from host: %s\n" % msg[1])
    return 5
  
  # this is incredibly inefficient way of concatenating a string but whatever
  serverlist = ""
  
  while 1:
    data = sock.recv(256) # recevie up to 256 bytes at a time
    if not data: break # sock.recv will return an empty string when the server closes the connection
    serverlist += data # and append it to our string we're growing.
   
  if (len(serverlist)==0):
    sys.stderr.write("Error, 0 bytes received from server list!  No servers up?")
    return 6
  
  sys.stdout.write("Recieved %i bytes from server\n" % len(serverlist))
  
  # parse this.  each server takes 12 bytes, so chomp it up until less than 12 remains
  # note that I'm performing a silly trick here, by interpretting the four-byte integer
  # inet-address as four seperate bytes so I can print it out nicely.  If I was going
  # to actually connect I'd probably keep it as the inet-addr and read it as <IIB instead 
  curpos = 0 # start at beginning
  listlen = len(serverlist)
  
  #lets start an XML doc.
  doc = xml.dom.minidom.Document()
  head_element = doc.createElement("serverlist")
  head_element.setAttribute("localtime",str(time.localtime()))
  head_element.setAttribute("mktime",str(time.mktime(time.localtime())))
  head_element.setAttribute("players",str(players_playing))
  doc.appendChild(head_element)
  
  while (curpos + 12 <= listlen): #while theres more than or exactly 12 bytes left
    i1,i2,i3,i4, port, flavor = struct.unpack("<BBBBIB",serverlist[curpos:curpos+9])
    sockaddr_as_string = ("%i.%i.%i.%i" % (i1,i2,i3,i4))
    curpos = curpos + 12 # advance the reading by the size of the structure
    #as you parse each server, we may as well ping it right here and now.
    # create a UDP socket with that ip and port
    pingsock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    # send the specially crafted "ping packet"
    # lets use time clock
    starttime = time.clock()
    packetrequester = struct.pack("<BI",2,(int)(time.clock() * 1000))
    sys.stdout.write("PINGING Server ip %s port %i flavor %i\n" % (sockaddr_as_string,port,flavor))
    pingsock.sendto(packetrequester,(sockaddr_as_string,port))
    pingsock.settimeout(3)
    server = doc.createElement("server")
    server.setAttribute("ip",sockaddr_as_string)
    server.setAttribute("port",str(port))
    # receive the ping response.
    try:
      pingresponse, addressfrom = pingsock.recvfrom(229)
    except socket.error, msg:
      sys.stderr.write("Server timed out...\n")
      server.setAttribute("responding","0")
      server.setAttribute("flavor",str(flavor))
      head_element.appendChild(server)
      continue
    
    pingsock.close()
    endtime = time.clock()
    
    try:
      # parse it using the layout described int the wiki.  Mind the padding!
      firstpiece = pingresponse[0:5]
      secondpiece = pingresponse[5:]
      bigfatparse = struct.unpack("<32s32sBBB64s20sxIIBBBB16sIIIIB20s3BBxxx",secondpiece)
    except struct.error, msg:
      sys.stderr.write("Unable to parse server reply\n")
      server.setAttribute("responding","0")
      head_element.appendChild(server)
      continue
    
    # now save various fields to the XML
    
    sys.stdout.write("Server name: %s\n" % (bigfatparse[0]))
    sys.stdout.write("Server game type: %s\n" % (bigfatparse[1]))
    sys.stdout.write("Players: %i/%i\n" % (bigfatparse[2],bigfatparse[3]))
    sys.stdout.write("Map name: %s\n" % (bigfatparse[5]))
    sys.stdout.write("Version: %s\n" % (bigfatparse[13]))
    sys.stdout.write("Skill Level: %i\n" % (bigfatparse[23]))
   
    server.setAttribute("responding","1")
    server.setAttribute("servername",bigfatparse[0].replace('\0',""))
    server.setAttribute("gametype",bigfatparse[1].replace('\0',""))
    server.setAttribute("flavor",str(flavor))
    server.setAttribute("playercount",str(bigfatparse[2]))
    server.setAttribute("maxplayercount",str(bigfatparse[3]))
    server.setAttribute("mapname",bigfatparse[5].replace('\0',""))
    server.setAttribute("version",bigfatparse[13].replace('\0',""))
    server.setAttribute("skill",str(bigfatparse[23]))
    
    head_element.appendChild(server)
  
  try:
    xmlfile = file(FTP_UPLOAD_FILE,"wb")
  except IOError:
    sys.stdout.write("Unable to open the file for writing\n")
    return 7
  #after this line, the file is now open so we mut close it.
  try:
    doc.writexml(writer=xmlfile,encoding="UTF-8")
  except IOError:
    sys.stdout.write("Unable to write to ther list file to save!\n")
    xmlfile.close() # have to close it since its now open and were returning
    return 7
  xmlfile.close()
    
  # save this xml file to a ftp site
  
  if (UPLOAD_TO_FTP is True):
    try:
      readfile = file(FTP_UPLOAD_FILE,"rb")
      try:
        if (UPLOAD_TO_FTP is True):
          try:
            ftpconnection = ftplib.FTP()
            ftpconnection.set_debuglevel(1)
            ftpconnection.connect(FTP_UPLOAD_HOST,FTP_UPLOAD_PORT)
            ftpconnection.login(FTP_UPLOAD_USER,FTP_UPLOAD_PASS)
            ftpconnection.cwd(FTP_UPLOAD_PATH)
            ftpconnection.storbinary("STOR " + FTP_UPLOAD_FILE,readfile)
            ftpconnection.quit()
          except ftplib.all_errors, e:
            sys.stdout.write(str(e))
      finally:
        readfile.close()
    except IOError:
      sys.stdout.write("Unable to read or open the file or something...\n")
      return 8
  
  return 0 # exit with success

DoTheEntireThing()
#try:
#  while 1:
#    DoTheEntireThing()
#    sys.stdout.write("Waiting for 5 minutes before going again... ctrl+C to quit\n")
#    time.sleep(60*5)
#except KeyboardInterrupt:
#  sys.stdout.write("Bye now!")
