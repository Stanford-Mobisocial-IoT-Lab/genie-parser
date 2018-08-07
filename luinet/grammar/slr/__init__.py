# Copyright 2017 The Board of Trustees of the Leland Stanford Junior University
#
# Author: Giovanni Campagna <gcampagn@cs.stanford.edu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>. 

# special tokens start with a space
# so they sort earlier than all other tokens
PAD_TOKEN = ' 0PAD' 
EOF_TOKEN = ' 1EOF'
START_TOKEN = ' 2START'
PAD_ID = 0
EOF_ID = 1
START_ID = 2

# codes for actions in the action table
# the values are chosen to be somewhat compatible with t2t's
# opinion of what encodings should look like
INVALID_CODE = PAD_ID
ACCEPT_CODE = EOF_ID
SHIFT_CODE = 2
REDUCE_CODE = 3