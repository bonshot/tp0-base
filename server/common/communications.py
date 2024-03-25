# This module contains the communication functions for the server. The main
# focus of the communication functions is to send and receive messages from
# the client avoiding short-reads and short-writes.


def send_message(sock, msg):
    """
    Send a message to a specific socket

    This function sends a message to a specific socket. If the message
    is not sent completely, the function will keep trying to send the
    remaining data until all the data is sent.

    :param sock: The socket to send the message to
    :param msg: The message to send

    :return: True if the message was sent successfully, False otherwise
    """
    total_sent = 0
    msg_len = len(msg)
    header = f"{msg_len}"
    final_msg = header + "|" + msg

    while total_sent < msg_len:
        sent = sock.send(final_msg[total_sent:].encode('utf-8'))
        if sent == 0:
            return False
        total_sent += sent
    
    return True

def read_header(sock):
    """ 
    Read the header of the message from the socket and returns
    it as an integer
    """
    header = ""
    while True:
        char = sock.recv(1).decode('utf-8')
        if char == "|":
            break
        header += char
    return int(header)

def receive_message(sock):
    """
    Receive a message from a specific socket

    This function receives a message from a specific socket. If the
    message is not received completely, the function will keep trying
    to receive the remaining data until all the data is received according to the header.

    :param sock: The socket to receive the message from

    :return: The message received from the socket
    """
    msg_len = 0
    header = read_header(sock)
    msg_len = int(header)
    msg = b''
    total_received = 0
    while total_received < msg_len:
        received = sock.recv(msg_len - total_received)
        if received == "":
            return ""
        total_received += len(received)
        msg += received
    return msg


